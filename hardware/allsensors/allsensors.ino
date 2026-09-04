/*
   ============================================================================
   BABY MONITORING — Heart Rate (BPM) + SpO2 (%)
   ============================================================================
   Sensor  : GY-MAX30102 (I2C 0x57, pakai library MAX30105 - kompatibel)
             DHT22 (suhu & kelembaban ruang), DS18B20 (suhu probe)
   Display : OLED SSD1306 128x64 (I2C 0x3C), 4 halaman ganti otomatis tiap 3 detik
   Board   : ESP8266 (NodeMCU / Wemos D1 Mini)
   Wiring  : SDA = D2 (GPIO4), SCL = D1 (GPIO5), VIN sensor & OLED = 3V3
             DHT22 data   = D5 (GPIO14)
             DS18B20 data = D6 (GPIO12), resistor pull-up 4.7k ke 3V3
             Button       = D7 (GPIO13) ke GND (internal pull-up, tanpa resistor)

   HALAMAN OLED (ganti otomatis tiap 3 detik, tanpa button):
     1. PULSE : SpO2 + BPM + hati kedip (layar utama)
     2. RUANG : suhu & kelembaban ruang (DHT22)
     3. PROBE : suhu probe DS18B20
     4. SEMUA : ringkasan semua sensor dalam satu layar

   Algoritma HR/SpO2 : Robert Fraczkiewicz (RF) — file algorithm_by_RF.h/.cpp
                       di folder sketch ini, sudah dimodifikasi untuk modul ini
                       (bandpass filter, pencarian puncak lokal, anti-oktaf).
   Kedip ikon hati   : checkForBeat() dari heartRate.h (SparkFun), jalan
                       real-time per sampel saat buffer diisi.

   Library yang harus terpasang (Library Manager):
     - SparkFun MAX3010x Pulse and Proximity Sensor Library
     - Adafruit SSD1306
     - Adafruit GFX Library
     - DHT sensor library (Adafruit)
     - OneWire
     - DallasTemperature

   CATATAN HARDWARE (hasil pengukuran 2026-07-17):
     Modul GY-MAX30102 ini memakai die CLONE yang menyimpang dari datasheet:
     - Diminta 200 sps hanya menghasilkan ~80 sps -> averaging dimatikan,
       algoritma RF disetel FS=80 (lihat algorithm_by_RF.h).
     - ADC range wajib 16384 nA; dengan 4096 sinyal IR saturasi (puncak
       denyut kepotong, algoritma gagal).
     Kalau ganti modul sensor, ukur ulang: lihat "fill=..ms" di Serial,
     harus ~4000ms untuk siklus penuh (320 sampel @ 80 Hz).

   ================= CARA KALIBRASI MANUAL SpO2 (regresi R vs SpO2) ==========
   1. Set SERIAL_CSV_LOG = 1 di bawah, upload ulang.
   2. Jepit sensor di satu jari, pulse oximeter komersial di jari lain
      (tangan yang sama, badan diam).
   3. Buka Serial Monitor 115200. Tiap ~2 detik keluar baris CSV:
         t,R,SpO2_hitung,BPM
   4. Salin baris-baris saat sinyal stabil ke spreadsheet, tambah kolom
      SpO2_ref (angka oximeter pembanding saat itu). Kumpulkan 15-20 pasang;
      variasikan kalau bisa (napas normal vs tahan napas 20-30 detik).
   5. Regresi linear SpO2_ref = A - B*R:
      - Spreadsheet: B = -SLOPE(SpO2_ref, R), A = INTERCEPT(SpO2_ref, R)
      - Python: numpy.polyfit(R, SpO2_ref, 1) -> B = -slope, A = intercept
   6. Ganti SPO2_CAL_A / SPO2_CAL_B, set SERIAL_CSV_LOG = 0, upload ulang.

   ================= CARA UJI ================================================
   Bandingkan dengan pulse oximeter komersial pada kondisi:
   - Duduk diam 1-2 menit (target: BPM +-5, SpO2 +-2%)
   - Gerak ringan (nilai boleh "--", yang penting TIDAK ngaco)
   - Jari longgar (harus muncul "Cari sinyal...", bukan angka acak)
   ============================================================================
*/

// WiFi/HTTP HARUS di-include sebelum algorithm_by_RF.h: file itu #define FS 80,
// yang kalau didefinisikan lebih dulu akan bentrok dengan fs::FS di dalam
// ESP8266WiFi (CertStoreBearSSL.h). Urutan ini = fix-nya.
#include <ESP8266WiFi.h>        // WiFi ESP8266
#include <ESP8266HTTPClient.h>  // HTTP client utk kirim data ke backend
#include <WiFiClient.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>
#include <DHT.h>                // DHT22: suhu & kelembaban ruang
#include <OneWire.h>            // bus 1-wire utk DS18B20
#include <DallasTemperature.h>  // DS18B20: suhu probe
#include "MAX30105.h"
#include "heartRate.h"        // checkForBeat(): deteksi detak real-time
#include "algorithm_by_RF.h"  // dipertahankan utk konstanta buffer RFA_BUFFER_SIZE
#include "spo2_algorithm.h"   // algoritma Maxim (SparkFun Example8): BPM & SpO2 langsung
#include "secrets.h"         // WIFI_SSID/PASSWORD, SERVER_URL, DEVICE_KEY (gitignored)

// ============================================================================
// KONSTANTA KALIBRASI & VALIDASI — semua yang perlu di-tune ada di blok ini
// ============================================================================

// --- Rumus SpO2 = SPO2_CAL_A - SPO2_CAL_B * R ---
// A dikalibrasi offset 2026-07-17: jangkar fisiologis (istirahat sehat=97.5%)
// pada median R=0.415 dari 57 siklus valid / 3 menit rekaman.
// B masih nilai literatur — memperbaiki slope butuh regresi dengan oximeter
// pembanding (prosedur di header atas).
#define SPO2_CAL_A           104.6f
#define SPO2_CAL_B           17.0f

// --- Mode output serial ---
#define SERIAL_CSV_LOG       0     // 1 = CSV utk kalibrasi, 0 = output normal
#define DEBUG_RAW            0     // 1 = dump isi buffer mentah tiap siklus
                                   //     (utk analisis sinyal offline/Python)

// --- Range fisiologis: nilai di luar ini dibuang, tampilan tidak di-update ---
#define BPM_MIN              40
#define BPM_MAX              180
#define SPO2_MIN             70.0f
#define SPO2_MAX             100.0f
#define R_MIN                0.4f  // ratio-of-ratios yang masuk akal
#define R_MAX                1.0f

// --- Deteksi jari & kualitas sinyal ---
#define FINGER_IR_THRESHOLD  30000 // IR DC di bawah ini = tidak ada jari
#define MIN_IR_PEAK_TO_PEAK  300   // amplitudo AC minimum; di bawah ini
                                   // tampil "Cari sinyal...", tidak dihitung

// --- Smoothing tampilan: median dari N hasil valid terakhir ---
#define MEDIAN_WINDOW        5

// --- Konsistensi detak (utk kedip hati): interval antar detak (IBI) ---
#define IBI_TOLERANCE        0.25f // tolak detak yang beda >25% dari rata-rata
#define IBI_MIN_MS           330   // ~180 bpm
#define IBI_MAX_MS           1500  // ~40 bpm

// --- LED sensor: 0-255, ~0.2mA/step ---
// Naikkan ke ~90-127 kalau sinyal lemah; turunkan kalau IR raw saturasi
// (mendekati 262143 = mentok ADC 18-bit).
#define LED_BRIGHTNESS       60

// ============================================================================
// KONFIGURASI WIFI & BACKEND — WAJIB diisi sesuai jaringan & server kamu
// ============================================================================
// --- IDENTITAS PER-ALAT (ganti bagian ini tiap flash device berbeda) ---
// Cuma dipakai utk hostname WiFi ('esp-inc1' di daftar client router). Identitas
// yang dipakai backend adalah DEVICE_KEY di secrets.h, bukan label ini.
#define INCUBATOR_ID     "inc1"    // posisi inkubator (inc1/inc2) — TETAP
#define STATIC_IP_LAST   2         // oktet akhir IP statis alat (inc1=2, inc2=3). JANGAN 1 (itu router).

// BABY_ID sudah DIHAPUS. Dulu ikut dikirim di payload dan harus di-REFLASH tiap
// ganti bayi — langkah manual yang gampang kelewat, dan kalau kelewat, pembacaan
// masuk ke bayi yang salah. Sekarang backend menentukan bayi dari penempatan
// aktif di database, jadi ganti bayi cukup lewat aplikasi. Jangan dihidupkan lagi.

// --- JARINGAN ---
// WIFI_SSID / WIFI_PASSWORD / SERVER_URL / DEVICE_KEY ada di secrets.h
// (gitignored). Salin secrets.example.h -> secrets.h lalu isi.
#define POST_INTERVAL_MS 3000               // kirim data ke backend tiap 3 detik

// --- IP STATIS (nyalakan saat sudah pindah ke router Advan 192.168.0.x) ---
#define USE_STATIC_IP    1         // 0 = DHCP, 1 = IP statis (inc1 = 192.168.0.2)
#define STATIC_SUBNET    192,168,0 // 3 oktet awal subnet router. IP alat = subnet.STATIC_IP_LAST

// --- OLED: ganti halaman OTOMATIS (button dihapus) ---
#define MODE_INTERVAL_MS 3000               // cycle halaman OLED tiap 3 detik

// ============================================================================
// HARDWARE & STATE GLOBAL
// ============================================================================

#define I2C_SDA        D2
#define I2C_SCL        D1
#define DHT_PIN        D5   // data DHT22
#define ONEWIRE_PIN    D6   // data DS18B20 (+ pull-up 4.7k ke 3V3)
#define OLED_ADDRESS   0x3C
#define SCREEN_WIDTH   128
#define SCREEN_HEIGHT  64

#define ENV_READ_INTERVAL_MS  2000  // jeda baca DHT22/DS18B20 (DHT22 max ~0.5Hz)

MAX30105 sensor;
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
DHT dht(DHT_PIN, DHT22);
OneWire oneWire(ONEWIRE_PIN);
DallasTemperature probeSensor(&oneWire);

// --- Halaman OLED, diganti otomatis tiap MODE_INTERVAL_MS (tanpa button) ---
enum Page { PAGE_PULSE, PAGE_ROOM, PAGE_PROBE, /* PAGE_ALL (SUMMARY) dinonaktifkan */ PAGE_COUNT };
Page currentPage = PAGE_PULSE;

// --- Nilai sensor lingkungan (NAN = belum ada / sensor error -> tampil "--") ---
float roomTempC    = NAN;  // suhu ruang, DHT22
float roomHumidity = NAN;  // kelembaban ruang %, DHT22
float probeTempC   = NAN;  // suhu probe, DS18B20

// Buffer sampel utk algoritma RF: RFA_BUFFER_SIZE = FS*ST = 80Hz * 4s = 320
uint32_t irBuffer[RFA_BUFFER_SIZE];
uint32_t redBuffer[RFA_BUFFER_SIZE];

// Sliding window: siklus pertama isi buffer penuh (4s), siklus berikutnya
// geser separuh lalu isi separuh baru (2s) -> hasil baru tiap ~2 detik.
bool bufferPrimed = false;
bool maximPrimed  = false;  // sudah isi 100 sampel awal utk algoritma Maxim?

// Status sinyal, dipakai utk baris status OLED & serial
enum SignalState { NO_FINGER, SEARCHING, MEASURING };
SignalState signalState = NO_FINGER;

// Nilai yang tampil di OLED (0 = belum ada -> tampil "--").
// Hanya di-update oleh hasil yang lolos semua validasi, jadi saat siklus
// gagal layar menahan nilai valid terakhir, bukan menampilkan angka acak.
int   displayBpm  = 0;
float displaySpo2 = 0;

// Riwayat hasil valid terakhir utk filter median (anti nilai meloncat)
float bpmHistory [MEDIAN_WINDOW]; int bpmHistoryCount  = 0;
float spo2History[MEDIAN_WINDOW]; int spo2HistoryCount = 0;

// Deteksi detak real-time (untuk kedip ikon hati, bukan untuk nilai BPM)
uint32_t lastBeatTimeMs     = 0;  // millis() saat detak valid terakhir
float    avgBeatIntervalMs  = 0;  // rata-rata berjalan interval antar detak
uint32_t heartIconUntilMs   = 0;  // ikon hati tampil sampai millis() ini
bool     heartIconVisible   = false;

// Diagnostik (ikut tercetak di serial):
uint32_t fillDurationMs = 0;  // lama pengisian buffer -> cek sample rate riil
uint32_t irPeakToPeak   = 0;  // amplitudo sinyal IR -> cek kualitas kontak

// ============================================================================
// UTIL: filter median
// ============================================================================

// Fungsi: masukkan nilai baru ke array riwayat (geser keluar yang tertua
// kalau sudah penuh MEDIAN_WINDOW).
void pushHistory(float *history, int *count, float value) {
  if (*count < MEDIAN_WINDOW) {
    history[(*count)++] = value;
  } else {
    memmove(history, history + 1, (MEDIAN_WINDOW - 1) * sizeof(float));
    history[MEDIAN_WINDOW - 1] = value;
  }
}

// Fungsi: median dari isi array riwayat (salin + insertion sort kecil).
// Median dipilih (bukan rata-rata) karena kebal terhadap satu nilai outlier.
float medianOf(const float *history, int count) {
  float sorted[MEDIAN_WINDOW];
  memcpy(sorted, history, count * sizeof(float));
  for (int i = 1; i < count; i++) {
    float v = sorted[i];
    int j = i - 1;
    while (j >= 0 && sorted[j] > v) { sorted[j + 1] = sorted[j]; j--; }
    sorted[j + 1] = v;
  }
  return sorted[count / 2];
}

// Fungsi: buang semua state pengukuran (dipanggil saat jari lepas) supaya
// sesi berikutnya mulai bersih, tidak membawa nilai lama.
void resetMeasurement() {
  bpmHistoryCount = spo2HistoryCount = 0;
  displayBpm = 0; displaySpo2 = 0;
  avgBeatIntervalMs = 0; lastBeatTimeMs = 0;
  heartIconUntilMs = 0;
  bufferPrimed = false;
  maximPrimed  = false;
}

// ============================================================================
// OLED
// ============================================================================

// Fungsi: lebar teks font default dalam pixel (6 px per karakter per size),
// dipakai untuk menaruh teks di tengah layar/kolom.
int textWidth(const char *s, int size) { return strlen(s) * 6 * size - size; }

// Fungsi: ikon hati kecil (muat di header bar 12px), warna bisa dipilih.
void drawHeartIcon(int x, int y, uint16_t color) {
  display.fillCircle(x + 2, y + 3, 2, color);
  display.fillCircle(x + 6, y + 3, 2, color);
  display.fillTriangle(x, y + 4, x + 8, y + 4, x + 4, y + 10, color);
}

// Fungsi: header bar putih di atas layar — judul halaman (teks hitam),
// ikon hati kedip, dan 4 titik indikator halaman di kanan (titik besar =
// halaman yang sedang aktif).
void drawHeaderBar(const __FlashStringHelper *title, bool showHeart) {
  display.fillRect(0, 0, SCREEN_WIDTH, 12, WHITE);
  display.setTextColor(BLACK);
  display.setTextSize(1);
  display.setCursor(3, 2);
  display.print(title);

  if (showHeart) drawHeartIcon(86, 0, BLACK);

  for (int i = 0; i < PAGE_COUNT; i++) {
    int x = SCREEN_WIDTH - (PAGE_COUNT - i) * 7;
    if (i == (int)currentPage) display.fillCircle(x, 5, 2, BLACK);
    else                       display.drawPixel(x, 5, BLACK);
  }
  display.setTextColor(WHITE);  // kembalikan utk isi halaman
}

// Fungsi: tulis angka float 1 desimal, atau "--" kalau NAN (sensor error).
void printValueOrDash(float value) {
  if (isnan(value)) display.print(F("--"));
  else              display.print(value, 1);
}

// Fungsi: simbol derajat (lingkaran kecil) + huruf C, menyambung posisi
// kursor terakhir. textSize = ukuran teks yang sedang dipakai.
void printDegreeC(uint8_t textSize) {
  int x = display.getCursorX(), y = display.getCursorY();
  display.drawCircle(x + textSize, y + textSize, textSize, WHITE);
  display.setCursor(x + 2 * textSize + 3, y);
  display.print('C');
}

// Fungsi: tulis teks size-1 rata tengah horizontal pada baris y.
void printCentered(const char *s, int y) {
  display.setTextSize(1);
  display.setCursor((SCREEN_WIDTH - textWidth(s, 1)) / 2, y);
  display.print(s);
}

// Fungsi: teks status jari di bawah halaman pulse — 1 baris, singkat.
void drawFingerStatus() {
  switch (signalState) {
    case NO_FINGER: printCentered("Place finger",   54); break;
    case SEARCHING: printCentered("Searching...",   54); break;
    default:        printCentered("Finger detected", 54); break;
  }
}

// ---------------------------------------------------------------------------
// Halaman 1 — PULSE OXIMETER: dua kolom dipisah garis — HR (BPM) di KIRI,
// SpO2 di kanan — angka besar di tengah kolom, status jari di bawah.
// Halaman ini tetap tampil lengkap saat tidak ada jari — nilainya "--".
// ---------------------------------------------------------------------------
void drawPagePulse() {
  display.drawFastVLine(64, 16, 32, WHITE);   // pembatas dua kolom

  display.setTextSize(1);
  display.setCursor(15, 17);  display.print(F("HR bpm"));
  display.setCursor(78, 17);  display.print(F("SpO2 %"));

  char buf[8];
  display.setTextSize(3);
  if (displayBpm > 0) snprintf(buf, sizeof buf, "%d", displayBpm);
  else                strcpy(buf, "--");
  display.setCursor((64 - textWidth(buf, 3)) / 2, 28);        // tengah kolom kiri
  display.print(buf);

  if (displaySpo2 > 0) snprintf(buf, sizeof buf, "%d", (int)(displaySpo2 + 0.5f));
  else                 strcpy(buf, "--");
  display.setCursor(64 + (64 - textWidth(buf, 3)) / 2, 28);   // tengah kolom kanan
  display.print(buf);

  drawFingerStatus();
}

// ---------------------------------------------------------------------------
// Halaman 2 — SUHU RUANGAN (DHT22): dua blok berlabel jelas —
// "Suhu" dengan nilai besar, lalu "Kelembapan" dengan nilai besar.
// ---------------------------------------------------------------------------
void drawPageRoom() {
  display.setTextSize(1);
  display.setCursor(4, 14);
  display.print(F("Temperature"));

  display.setTextSize(2);
  display.setCursor(30, 23);
  printValueOrDash(roomTempC);
  printDegreeC(2);

  display.setTextSize(1);
  display.setCursor(4, 40);
  display.print(F("Humidity"));

  display.setTextSize(2);
  display.setCursor(30, 49);
  printValueOrDash(roomHumidity);
  display.print(F(" %"));
}

// ---------------------------------------------------------------------------
// Halaman 3 — SUHU TUBUH (DS18B20): satu angka besar di tengah layar.
// ---------------------------------------------------------------------------
void drawPageProbe() {
  char buf[8];
  if (isnan(probeTempC)) strcpy(buf, "--");
  else                   dtostrf(probeTempC, 0, 1, buf);

  // lebar total = angka + simbol derajat + huruf C, supaya pas di tengah
  int w = textWidth(buf, 3) + (2 * 3 + 3) + 18;
  display.setTextSize(3);
  display.setCursor((SCREEN_WIDTH - w) / 2, 30);
  display.print(buf);
  printDegreeC(3);
}

// ---------------------------------------------------------------------------
// Halaman 4 — SUMMARY: ringkasan semua sensor, label kiri nilai kanan.
// HR & SpO2 kasih catatan "no finger" di sampingnya saat jari belum menempel.
// ---------------------------------------------------------------------------
#if 0  // === SUMMARY page dinonaktifkan — mau tampil 3 halaman saja ===
void drawPageAll() {
  display.setTextSize(1);
  bool noFinger = (signalState == NO_FINGER);

  display.setCursor(4, 17);   display.print(F("HR"));
  display.setCursor(46, 17);
  if (displayBpm > 0) { display.print(displayBpm); display.print(F(" bpm")); }
  else { display.print(F("-- ")); if (noFinger) display.print(F("*no finger")); }

  display.setCursor(4, 29);   display.print(F("SpO2"));
  display.setCursor(46, 29);
  if (displaySpo2 > 0) { display.print((int)(displaySpo2 + 0.5f)); display.print(F(" %")); }
  else { display.print(F("-- ")); if (noFinger) display.print(F("*no finger")); }

  display.setCursor(4, 41);   display.print(F("Room"));
  display.setCursor(46, 41);
  printValueOrDash(roomTempC);   display.print(F("C "));
  printValueOrDash(roomHumidity); display.print('%');

  display.setCursor(4, 53);   display.print(F("Body"));
  display.setCursor(46, 53);
  printValueOrDash(probeTempC);  display.print('C');
}
#endif  // drawPageAll (SUMMARY dinonaktifkan)

// Fungsi: gambar seluruh layar — header bar + isi sesuai halaman aktif.
// Hati kedip ikut di header (halaman pulse & ringkasan).
void drawScreen(bool showHeart) {
  display.clearDisplay();
  switch (currentPage) {
    case PAGE_PULSE: drawHeaderBar(F("PULSE OXIMETER"), showHeart); drawPagePulse(); break;
    case PAGE_ROOM:  drawHeaderBar(F("ROOM CLIMATE"),  false);      drawPageRoom();  break;
    case PAGE_PROBE: drawHeaderBar(F("BODY TEMP"),     false);      drawPageProbe(); break;
    // SUMMARY dinonaktifkan — cuma tampil 3 halaman (PULSE, ROOM, PROBE):
    // default:      drawHeaderBar(F("SUMMARY"), showHeart); drawPageAll(); break;
  }
  display.display();
}

// ============================================================================
// AUTO-CYCLE HALAMAN OLED & SENSOR LINGKUNGAN
// ============================================================================

// Fungsi: ganti halaman OLED OTOMATIS tiap MODE_INTERVAL_MS (pengganti button).
// Non-blocking (millis). Dipanggil sesering mungkin — termasuk per-sampel saat
// pengisian buffer — supaya cadence tetap jalan walau lagi ngukur vital.
void autoCycleMode() {
  static uint32_t lastModeChange = 0;
  if (millis() - lastModeChange < MODE_INTERVAL_MS) return;
  lastModeChange = millis();
  currentPage = (Page)((currentPage + 1) % PAGE_COUNT);
  drawScreen(heartIconVisible);
#if !SERIAL_CSV_LOG
  Serial.print(F("[MODE] page ")); Serial.println((int)currentPage);
#endif
}

// Fungsi: baca DHT22 & DS18B20 tiap ENV_READ_INTERVAL_MS (2 detik).
// DS18B20 dibaca ASINKRON: hasil yang diambil adalah konversi yang diminta
// 2 detik sebelumnya (konversi butuh ~750ms), lalu langsung minta konversi
// baru — jadi tidak pernah memblokir sampling MAX30102.
// Gagal baca -> NAN -> tampil "--" di OLED.
void readEnvironmentSensors() {
  static uint32_t lastReadMs = 0;
  if (millis() - lastReadMs < ENV_READ_INTERVAL_MS) return;
  lastReadMs = millis();

  roomTempC    = dht.readTemperature();  // NAN otomatis kalau gagal
  roomHumidity = dht.readHumidity();
  // Jalur data mengambang (tanpa pull-up) terbaca all-zero, dan checksum-nya
  // kebetulan lolos (0==0) sehingga library kira sukses -> suhu 0 & RH 0.
  // Ruangan nyata tak mungkin 0C & 0%RH sekaligus, jadi anggap gagal -> "--".
  if (roomTempC == 0.0f && roomHumidity == 0.0f) {
    roomTempC = roomHumidity = NAN;
  }

  // WiFi ISR sesekali merusak timing bit-bang OneWire -> baca CRC gagal (-127),
  // bikin nilai probe "hilang" (--) padahal sensor terpasang. Baca ulang
  // scratchpad beberapa kali (konversi lama masih valid, tak perlu tunggu 750ms)
  // sebelum menyerah. Ini fix intermittent DS18B20 saat WiFi aktif.
  float t = probeSensor.getTempCByIndex(0);
  for (int i = 0; i < 4 && t == DEVICE_DISCONNECTED_C; i++) {
    t = probeSensor.getTempCByIndex(0);
  }
  probeTempC = (t == DEVICE_DISCONNECTED_C) ? NAN : t;
  probeSensor.requestTemperatures();     // mulai konversi utk pembacaan berikutnya
}

// ============================================================================
// DETEKSI DETAK REAL-TIME (kedip ikon hati)
// ============================================================================

// Fungsi: proses satu sampel IR dengan checkForBeat(). Kalau terdeteksi detak,
// saring dulu dengan aturan konsistensi IBI (interval antar detak) supaya
// noise tidak dianggap detak, baru nyalakan ikon hati 150ms.
// Catatan: ini HANYA untuk kedip hati; nilai BPM di layar dihitung terpisah
// oleh algoritma RF yang jauh lebih tahan noise.
void detectBeatForIcon(uint32_t irSample) {
  if (!checkForBeat((int32_t)irSample)) return;

  uint32_t now = millis();
  uint32_t interval = now - lastBeatTimeMs;
  lastBeatTimeMs = now;

  if (interval < IBI_MIN_MS || interval > IBI_MAX_MS) return;   // di luar 40-180 bpm
  if (avgBeatIntervalMs > 0 &&
      fabsf((float)interval - avgBeatIntervalMs) > IBI_TOLERANCE * avgBeatIntervalMs)
    return;                                                     // beda >25% dari rata-rata = noise

  // update rata-rata berjalan (pembobotan 80/20) dan nyalakan hati
  avgBeatIntervalMs = (avgBeatIntervalMs > 0)
                        ? (0.8f * avgBeatIntervalMs + 0.2f * interval)
                        : interval;
  heartIconUntilMs = now + 150;
}

// Fungsi: sinkronkan ikon hati dengan waktunya. Redraw layar HANYA saat
// status hati berubah supaya tidak mengganggu timing sampling
// (redraw OLED ~30ms; FIFO sensor 32 sampel @80Hz = 400ms slack -> aman).
void updateHeartIcon() {
  bool shouldShow = millis() < heartIconUntilMs;
  if (shouldShow != heartIconVisible) {
    heartIconVisible = shouldShow;
    drawScreen(shouldShow);
  }
}

// ============================================================================
// SAMPLING
// ============================================================================

// Fungsi: isi irBuffer/redBuffer dari index startIndex sampai penuh, sambil
// menjalankan deteksi detak & kedip hati per sampel.
// Return false kalau jari lepas di tengah pengisian (IR turun di bawah
// threshold). Setelah penuh, hitung amplitudo peak-to-peak IR (ke variabel
// global irPeakToPeak) untuk cek kualitas sinyal.
// Fungsi: hidupin ulang MAX30102 kalau mati (LED off / hilang config).
void reinitSensor() {
  sensor.begin(Wire, I2C_SPEED_FAST);
  sensor.setup(LED_BRIGHTNESS, 2, 2, 50, 215, 16384);
#if !SERIAL_CSV_LOG
  Serial.println(F("[SENSOR] MAX30102 mati -> di-init ulang"));
#endif
}

// Fungsi: baca 1 sampel MAX30102. Return 0=ok, 1=jari lepas, 2=sensor STALL.
// Guard anti-freeze: FIFO tak mengisi > 100ms -> return 2 (bukan spin selamanya).
int readSample(int i) {
  uint32_t t0 = millis();
  while (!sensor.available()) {
    sensor.check();
    yield();
    if (millis() - t0 > 100) return 2;
  }
  redBuffer[i] = sensor.getRed();
  irBuffer[i]  = sensor.getIR();
  sensor.nextSample();
  if (irBuffer[i] < FINGER_IR_THRESHOLD) return 1;
  detectBeatForIcon(irBuffer[i]);
  updateHeartIcon();
  autoCycleMode();
  return 0;
}

#if 0  // fillSampleBuffer (RF) dinonaktifkan — Maxim pakai readSample
bool fillSampleBuffer(int startIndex) {
  for (int i = startIndex; i < RFA_BUFFER_SIZE; i++) {
    while (!sensor.available()) { sensor.check(); yield(); }
    redBuffer[i] = sensor.getRed();
    irBuffer[i]  = sensor.getIR();
    sensor.nextSample();

    if (irBuffer[i] < FINGER_IR_THRESHOLD) return false;  // jari lepas

    detectBeatForIcon(irBuffer[i]);
    updateHeartIcon();
    autoCycleMode();  // cycle halaman OLED tetap jalan selama pengukuran
  }

  uint32_t irMin = 0xFFFFFFFF, irMax = 0;
  for (int i = 0; i < RFA_BUFFER_SIZE; i++) {
    if (irBuffer[i] < irMin) irMin = irBuffer[i];
    if (irBuffer[i] > irMax) irMax = irBuffer[i];
  }
  irPeakToPeak = irMax - irMin;
  return true;
}
#endif  // fillSampleBuffer (RF)

// ============================================================================
// OUTPUT SERIAL
// ============================================================================

// Fungsi: cetak hasil satu siklus ke Serial.
// - Mode normal : baris lengkap utk debugging (raw, R, SpO2, BPM, diagnostik).
// - Mode CSV    : "t,R,SpO2,BPM" utk regresi kalibrasi di spreadsheet/Python.
#if 0  // printResult (RF) dinonaktifkan
void printResult(float R, float spo2, bool spo2Ok, int32_t bpm, bool bpmOk,
                 float pearsonCorrel) {
  float t = millis() / 1000.0f;
#if SERIAL_CSV_LOG
  Serial.print(t, 1);    Serial.print(',');
  Serial.print(R, 4);    Serial.print(',');
  Serial.print(spo2, 1); Serial.print(',');
  Serial.println(bpmOk ? bpm : 0);
#else
  Serial.print(F("[t="));       Serial.print(t, 1); Serial.print(F("s] "));
  Serial.print(F("IR_raw="));   Serial.print(irBuffer[RFA_BUFFER_SIZE - 1]);
  Serial.print(F(" RED_raw=")); Serial.print(redBuffer[RFA_BUFFER_SIZE - 1]);
  Serial.print(F(" | R="));     Serial.print(R, 3);
  Serial.print(F(" | SpO2="));  Serial.print(spo2, 0); Serial.print('%');
  Serial.print(spo2Ok ? F(" (valid)") : F(" (invalid)"));
  Serial.print(F(" | BPM="));   Serial.print(bpm);
  Serial.print(bpmOk ? F(" (valid)") : F(" (invalid)"));
  // Diagnostik:
  //   correl = korelasi Pearson RED vs IR (>0.8 = sinyal denyut sungguhan)
  //   fill   = lama isi buffer; siklus penuh ~4000ms, siklus geser ~2000ms.
  //            Kalau jauh dari itu, sample rate sensor berubah -> FS di
  //            algorithm_by_RF.h harus disesuaikan!
  //   pp     = amplitudo IR peak-to-peak (kualitas kontak jari)
  Serial.print(F(" | correl=")); Serial.print(pearsonCorrel, 2);
  Serial.print(F(" fill="));     Serial.print(fillDurationMs); Serial.print(F("ms"));
  Serial.print(F(" pp="));       Serial.print(irPeakToPeak);
  // sensor lingkungan ("nan" = gagal baca / belum terpasang)
  Serial.print(F(" | Room=")); Serial.print(roomTempC, 1);
  Serial.print(F("C "));       Serial.print(roomHumidity, 0);
  Serial.print(F("% Body=")); Serial.print(probeTempC, 1);
  Serial.println(F("C"));
#endif

#if DEBUG_RAW
  // Dump mentah utk analisis offline (Python): baris "IR,RED" per sampel
  Serial.println(F("RAWSTART"));
  for (int i = 0; i < RFA_BUFFER_SIZE; i++) {
    Serial.print(irBuffer[i]); Serial.print(','); Serial.println(redBuffer[i]);
  }
  Serial.println(F("RAWEND"));
#endif
}
#endif  // printResult (RF)

// ============================================================================
// KIRIM DATA KE BACKEND (WiFi + HTTP POST)
// ============================================================================

// Fungsi: connect ke WiFi dgn timeout 10s. TIDAK memblokir selamanya — kalau
// gagal, monitor tetap jalan offline dan ESP auto-retry di background;
// postToServer() cuma mengirim saat status sudah WL_CONNECTED.
void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.hostname("esp-" INCUBATOR_ID);       // muncul sbg 'esp-inc1' di daftar client router
#if USE_STATIC_IP
  IPAddress ip(STATIC_SUBNET, STATIC_IP_LAST);
  IPAddress gw(STATIC_SUBNET, 1);
  WiFi.config(ip, gw, IPAddress(255, 255, 255, 0), gw);  // IP statis, DNS = gateway
#endif
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print(F("WiFi connecting"));
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(250);
    Serial.print('.');
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print(F(" OK, IP=")); Serial.print(WiFi.localIP());
    Serial.print(F(" GW="));     Serial.print(WiFi.gatewayIP());
    Serial.print(F(" RSSI="));   Serial.println(WiFi.RSSI());
  } else {
    Serial.println(F(" gagal (lanjut offline, auto-retry di background)"));
  }
}

// Fungsi: tambah "key":num ke JSON, atau "key":null kalau NAN (sensor error)
// -> dashboard menampilkan "--" untuk nilai null.
static void appendNum(String &json, const char *key, float v, int decimals) {
  json += '"'; json += key; json += "\":";
  if (isnan(v)) json += "null";
  else          json += String(v, decimals);
}

// Fungsi: bangun payload JSON satu paket & POST ke backend. Nilai yang dikirim
// adalah nilai tampil terkini (displayBpm/displaySpo2 = 0 saat tidak ada jari).
// ponytail: JSON dirakit manual (5 field) — tak perlu ArduinoJson.
int postToServer() {
  if (WiFi.status() != WL_CONNECTED) return -1;

  // Payload jalur LEGACY (POST /api/sensors): bersarang, nama hardware, dan
  // inkubator ditentukan dari label incubator_id di bawah — bukan dari kunci.
  // Backend me-rename ds18b20/dht22 -> nama klinis di sisi sana.
  //
  // Konsekuensi yang perlu diketahui, bukan bug: rute ini tidak memeriksa
  // identitas siapa pun, jadi apa pun yang bisa menjangkau port bisa menulis
  // pembacaan; dan setiap baris tersimpan dengan device_id NULL, sehingga kartu
  // "Perangkat IoT" tetap berbunyi "Mengirim tanpa terdaftar" walau grafiknya
  // hidup. Server juga harus dijalankan dengan LEGACY_SENSOR_INGEST=true —
  // kalau tidak, rute ini menjawab 404 dan alat gagal tanpa suara.
  String json = "{";
  json += "\"incubator_id\":\"" INCUBATOR_ID "\",";
  json += "\"sensors\":{";
  // 0 bpm / 0% artinya "jari tidak terbaca", BUKAN nilai nol — backend
  // menormalkan 0 -> null supaya grafik memutus garis, bukan menggambar lantai.
  json += "\"heart_rate\":"; json += displayBpm;                 json += ',';
  json += "\"spo2\":";       json += (int)(displaySpo2 + 0.5f);  json += ',';
  appendNum(json, "ds18b20_temp",   probeTempC,   1); json += ',';
  appendNum(json, "dht22_temp",     roomTempC,    1); json += ',';
  appendNum(json, "dht22_humidity", roomHumidity, 0);
  json += "}}";

  WiFiClient client;
  HTTPClient http;
  http.begin(client, SERVER_URL);
  // Sengaja TIDAK mengirim X-Device-Key: /api/sensors mengabaikannya sepenuhnya.
  // Mengirimnya hanya menimbulkan kesan alat ini terautentikasi, padahal tidak.
  // DEVICE_KEY tetap ada di secrets.h untuk saat pindah ke /api/v1/telemetry.
  // Cap timeout: server tak terjangkau JANGAN sampai freeze loop 5s (default) —
  // itu yang bikin MAX30102 & button nge-lag. setTimeout() meng-cap connect+read
  // (dipakai sbg _client->setTimeout sebelum connect). POST sukses di LAN < 50ms.
  http.setTimeout(500);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(json);
#if !SERIAL_CSV_LOG
  Serial.print(F("[POST] ")); Serial.print(code); Serial.print(' '); Serial.println(json);
#endif
  http.end();
  return code;
}

// Fungsi: gate waktu — POST cuma tiap intervalMs. POST-nya blocking; timeout
// di-cap 500ms + backoff saat gagal supaya sampling/button tak nge-lag.
// ponytail: butuh 0 hitch bahkan saat server hidup? pindah async (ESPAsyncTCP)
// — belum perlu.
void maybePostToServer() {
  static uint32_t lastPostMs = 0;
  static uint32_t intervalMs = POST_INTERVAL_MS;
  if (millis() - lastPostMs < intervalMs) return;
  lastPostMs = millis();
  int code = postToServer();
  // Backoff saat gagal (mis. WiFi meng-isolasi client / server mati): naikkan
  // interval s/d 30s biar POST blocking tak bikin device nge-lag tiap 3 detik.
  // Sekali sukses -> balik ke interval normal.
  intervalMs = (code > 0) ? (uint32_t)POST_INTERVAL_MS
                          : min(intervalMs * 2, (uint32_t)30000);
}

// ============================================================================
// SETUP & LOOP
// ============================================================================

void setup() {
  Serial.begin(115200);

  // Bebaskan bus I2C kalau ada slave nyangkut: upload/reset bisa memutus
  // transaksi di tengah jalan, sensor menahan SDA low, dan semua I2C hang
  // saat boot (gejala: board membisu total). 9 pulsa SCL memaksa slave
  // menyelesaikan byte-nya dan melepas SDA.
  pinMode(I2C_SDA, INPUT_PULLUP);
  pinMode(I2C_SCL, OUTPUT);
  for (int i = 0; i < 9 && digitalRead(I2C_SDA) == LOW; i++) {
    digitalWrite(I2C_SCL, LOW);  delayMicroseconds(5);
    digitalWrite(I2C_SCL, HIGH); delayMicroseconds(5);
  }
  pinMode(I2C_SCL, INPUT_PULLUP);

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000);

  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS)) {
    Serial.println(F("OLED not detected, check wiring/I2C address!"));
    while (1) delay(10);
  }

  // OLED sudah siap -> bersihkan layar & tampilkan splash SEBELUM connect WiFi,
  // supaya TIDAK muncul isi RAM acak ("QR") selama WiFi konek (bisa s/d 10 detik).
  display.clearDisplay();
  display.setTextColor(WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);   display.println(F("Baby Monitor"));
  display.setCursor(0, 16);  display.println(F("Connecting WiFi..."));
  display.display();

  connectWiFi();   // OLED nampilin splash selama proses ini (bukan QR lagi)

  // JANGAN hang kalau MAX30102 gagal di-deteksi saat boot (mis. power drop) —
  // device tetap jalan, reinitSensor() di loop nyoba hidupin.
  if (!sensor.begin(Wire, I2C_SPEED_FAST))
    Serial.println(F("MAX30102 tidak terdeteksi saat boot -> lanjut, auto-retry di loop"));

  // Konfigurasi sensor utk algoritma Maxim: target ~25sps (FreqS=25).
  //   rate 50 / average 2 = 25sps efektif (clone sanggup 50 raw).
  //   adcRange 16384 : wajib; dgn 4096 sinyal saturasi & denyut kepotong.
  sensor.setup(LED_BRIGHTNESS, 2, 2, 50, 215, 16384);

  // Sensor lingkungan (button dihapus — halaman OLED cycle otomatis)
  dht.begin();
  probeSensor.begin();
  probeSensor.setResolution(11);            // 0.125°C, konversi ~375ms (default 12-bit ~750ms)
  probeSensor.setWaitForConversion(false);  // mode asinkron (lihat readEnvironmentSensors)
  probeSensor.requestTemperatures();        // mulai konversi pertama

#if SERIAL_CSV_LOG
  Serial.println(F("t,R,SpO2_calc,BPM"));
#else
  Serial.println(F("\nBaby Monitoring HR+SpO2 (RF algorithm) - not a medical device"));
#endif
  drawScreen(false);
}

void loop() {
  // --- 0. Hal-hal yang jalan tiap iterasi, ada jari maupun tidak ---
  autoCycleMode();
  readEnvironmentSensors();
  maybePostToServer();   // kirim ke backend tiap POST_INTERVAL_MS (time-gated)

  // --- 1. Cek jari (satu sampel cepat, sebelum komit isi buffer) ---
  sensor.check();
  if (sensor.getIR() < FINGER_IR_THRESHOLD) {
    if (signalState != NO_FINGER) {
      signalState = NO_FINGER;
      resetMeasurement();
    }
#if !SERIAL_CSV_LOG
    Serial.println(F("No finger detected, waiting..."));
#endif
    // Redraw supaya halaman suhu/kelembaban tetap update walau tanpa jari,
    // lalu tunggu 300ms sambil tetap cycle halaman (bukan delay buta).
    drawScreen(false);
    // cek MAX30102 masih hidup; kalau mati (nggak ada sampel 3 siklus) -> hidupin
    bool gotSample = false;
    for (int i = 0; i < 30; i++) {
      sensor.check();
      if (sensor.available()) { gotSample = true; sensor.nextSample(); }
      autoCycleMode();
      delay(10);
    }
    static int deadIdle = 0;
    if (!gotSample) { if (++deadIdle >= 3) { reinitSensor(); deadIdle = 0; } }
    else deadIdle = 0;
    return;
  }
  if (signalState == NO_FINGER) { signalState = SEARCHING; drawScreen(false); }

  // --- 2. Sampling MAX30102 pakai algoritma Maxim (SparkFun Example8) + guard ---
  // Buffer 100 sampel @ ~25sps. Pertama isi penuh 100; berikutnya buang 25 lama
  // + isi 25 baru -> hasil ~tiap 1 detik. readSample punya timeout (anti-freeze).
  const int MAXIM_LEN = 100;
  static int stallStreak = 0;
  int status = 0;               // 0=ok, 1=jari lepas, 2=stall
  if (!maximPrimed) {
    for (int i = 0; i < MAXIM_LEN && status == 0; i++) status = readSample(i);
    if (status == 0) maximPrimed = true;
  } else {
    for (int i = 25; i < MAXIM_LEN; i++) { redBuffer[i - 25] = redBuffer[i]; irBuffer[i - 25] = irBuffer[i]; }
    for (int i = 75; i < MAXIM_LEN && status == 0; i++) status = readSample(i);
  }
  if (status == 2) {            // sensor STALL -> bus/sensor bermasalah -> recover, JANGAN freeze
    if (++stallStreak >= 2) { reinitSensor(); stallStreak = 0; }
    signalState = NO_FINGER;
    drawScreen(false);
    return;
  }
  stallStreak = 0;
  if (status == 1) {            // jari lepas
    signalState = NO_FINGER;
    resetMeasurement();
    drawScreen(false);
    return;
  }

  // --- 3. Hitung HR & SpO2 (Maxim) — RAW, tampil LANGSUNG tanpa filter valid/invalid ---
  int32_t spo2, heartRate;
  int8_t  validSPO2, validHeartRate;
  maxim_heart_rate_and_oxygen_saturation(irBuffer, MAXIM_LEN, redBuffer,
                                         &spo2, &validSPO2, &heartRate, &validHeartRate);
  displayBpm  = (heartRate > 0) ? heartRate : 0;   // -999 (gagal) -> 0 -> tampil "--"
  displaySpo2 = (spo2 > 0)      ? spo2      : 0;

  signalState = MEASURING;
  drawScreen(heartIconVisible);
#if !SERIAL_CSV_LOG
  Serial.print(F("[RAW] BPM="));  Serial.print(heartRate);
  Serial.print(F(" (valid="));    Serial.print(validHeartRate);
  Serial.print(F(")  SpO2="));    Serial.print(spo2);
  Serial.print(F(" (valid="));    Serial.print(validSPO2); Serial.println(F(")"));
#endif
}
