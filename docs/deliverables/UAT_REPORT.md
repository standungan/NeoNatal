# Laporan Pengujian Sistem (UAT Report)

## Sistem Pemantauan Inkubator Bayi Terintegrasi Berbasis Internet of Things

| | |
|---|---|
| **Nama sistem** | Neonatal Care System — Sistem Monitoring Bayi pada Inkubator |
| **Versi dokumen** | 1.1 |
| **Tanggal pengujian** | 7 September 2026; pengujian tambahan 19 September 2026 (§3.5) |
| **Penguji (Bagian A)** | Pengembang — Sofyan Tandungan |
| **Penguji (Bagian B)** | Klien / tenaga medis penunjuk — **belum dijalankan** |
| **Dasar** | Kontrak Pasal 3.1 (deliverable) dan `docs/deliverables/SRS.md` |

---

## Peringatan penting tentang status dokumen ini

Dokumen ini terdiri atas dua bagian yang **berbeda statusnya**, dan pembedaan itu disengaja:

- **Bagian A — sudah dijalankan.** Pengujian otomatis dan verifikasi teknis yang benar-benar
  dieksekusi Pengembang pada tanggal di atas. Angkanya adalah keluaran program, bukan
  perkiraan.
- **Bagian B — belum dijalankan.** Skenario penerimaan yang harus dijalankan **oleh Klien**.
  Kolom hasilnya sengaja dikosongkan.

Bagian B tidak diisi Pengembang. UAT adalah pernyataan Klien bahwa sistem dapat diterima;
mengisinya sendiri akan membuat dokumen ini kehilangan seluruh maknanya. Dokumen ini baru
menjadi UAT Report yang lengkap setelah Bagian B diisi dan ditandatangani.

---

## 1. Tujuan dan Kriteria

### 1.1 Tujuan

Membuktikan bahwa sistem memenuhi kebutuhan pada `docs/deliverables/SRS.md` dan layak diserahterimakan
sesuai Kontrak Pasal 3.

### 1.2 Kriteria kelulusan tiap butir

| Nilai | Arti |
|---|---|
| **Lulus** | Hasil sesuai yang diharapkan, tanpa langkah tambahan. |
| **Lulus dengan catatan** | Hasil sesuai, tetapi ada perilaku yang perlu dicatat. |
| **Gagal** | Hasil tidak sesuai, atau butuh langkah di luar panduan. |
| **Tidak diuji** | Tidak dapat diuji pada lingkungan ini; sebabnya wajib ditulis. |

### 1.3 Kriteria penerimaan keseluruhan

Sistem diterima apabila seluruh butir Bagian B berstatus **Lulus** atau **Lulus dengan
catatan**, dan tidak ada butir **Gagal** yang menyangkut keselamatan data pasien.

---

## 2. Lingkungan Pengujian

| Komponen | Keterangan |
|---|---|
| Basis data | PostgreSQL, berisi data uji dan **3.685 pembacaan sensor nyata** pada Inkubator 01 |
| Backend | FastAPI, Python 3.10.11, `:8000` |
| Dashboard | Next.js 16.2.9 |
| Aplikasi mobile | Flutter 3.47.2 / Dart 3.13.2, target Android arm64 |
| Perangkat IoT | ESP8266 NodeMCU, arduino-cli 1.5.1, core esp8266 3.1.2 |
| Cara menjalankan | Tanpa Docker (`DEPLOYMENT.md` § Menjalankan tanpa Docker) |

Pengujian Bagian A dijalankan pada lingkungan pengembangan, bukan pada server produksi
Klien. Bagian B **harus** dijalankan pada server produksi.

---

## 3. Bagian A — Pengujian yang Sudah Dijalankan

Seluruh angka di bawah adalah keluaran program pada 7 September 2026.

### 3.1 Suite pengujian backend

| # | Suite | Cakupan | Butir | Hasil |
|---|---|---|---|---|
| A-1 | `smoke_check.py` | Seluruh modul backend menjawab; RBAC ditegakkan | 39 | **39/39 Lulus** |
| A-2 | `telemetry_check.py` | Seluruh cabang `POST /api/v1/telemetry` | 30 | **30/30 Lulus** |
| A-3 | `firmware_payload_check.py` | JSON persis yang dibangun `allsensors.ino` | 5 | **Lulus** |
| A-4 | `stream_check.py` | Penyebaran SSE dari telemetri ke klien | 14 | **14/14 Lulus** |
| A-5 | `alert_check.py` | Mesin peringatan ambang batas | 28 | **28/28 Lulus** |
| A-6 | `retention_check.py` | Peringkasan per menit dan pembersihan | 18 | **18/18 Lulus** |
| | | **Total** | **134** | **134 Lulus, 0 Gagal** |

Cara menjalankan ulang:

```bash
cd backend
for t in smoke telemetry firmware_payload stream alert retention; do
  ./venv/bin/python tests/${t}_check.py
done
```

### 3.2 Pembangunan dan analisis statis

| # | Butir | Hasil |
|---|---|---|
| A-7 | Build produksi dashboard (`next build`) | **Lulus** — 18 rute, tanpa galat |
| A-8 | Analisis statis aplikasi mobile (`flutter analyze`) | **Lulus** — *No issues found* |
| A-9 | Kompilasi firmware (`arduino-cli compile`) | **Lulus** — 0 galat; flash 26%, RAM 41%, IRAM 93% |

### 3.3 Verifikasi penerapan

| # | Butir | Hasil | Tanggal |
|---|---|---|---|
| A-10 | Kloning bersih dari repositori membangun basis data yang identik dengan produksi (17 tabel, nihil selisih) | **Lulus** | 4 Sep 2026 |
| A-11 | Suite `smoke_check` terhadap basis data hasil kloning bersih | **39/39 Lulus** | 4 Sep 2026 |
| A-12 | Stack Docker Compose menyala; `db` sehat sebelum backend mulai | **Lulus** | 4 Sep 2026 |
| A-13 | `smoke_check` terhadap stack kontainer | **39/39 Lulus** | 4 Sep 2026 |
| A-14 | Masuk melalui BFF dashboard kontainer dan membaca 9 inkubator | **Lulus** | 4 Sep 2026 |
| A-15 | Alamat server dan kunci perangkat benar tertanam di APK (diperiksa pada berkas biner) | **Lulus** | 4 Sep 2026 |

### 3.4 Ketertelusuran ke SRS

| Kebutuhan SRS | Dibuktikan oleh |
|---|---|
| F-4.1 – F-4.5 (autentikasi, otorisasi) | A-1 |
| F-4.10 – F-4.17 (asesmen klinis) | A-1 |
| F-4.18 – F-4.22 (telemetri) | A-2, A-3 |
| F-4.23 – F-4.25 (peringatan) | A-5 |
| F-4.26 – F-4.27 (laporan, PDF) | A-1 |
| F-4.28 – F-4.32 (administrasi) | A-1 |
| F-2.1 – F-2.5, D-1 – D-4 (basis data, retensi) | A-6, A-10 |
| F-3.1 – F-3.4 (server, migrasi) | A-10, A-12 |
| F-5.1 – F-5.4 (aplikasi mobile) | A-8, A-15 |
| F-6.1 – F-6.6 (dashboard) | A-7, A-14 |
| F-7.1 – F-7.8 (firmware) | A-3, A-9 |
| NF-3 (grafik 120 titik), NF-16 (volume bertahan) | A-4, A-12 |
| F-4.8, F-4.26, F-4.29, F-4.33 – F-4.37, F-6.3, F-6.7, F-6.8, D-8 (pemakaian ulang & arsip inkubator, SRS 1.4) | A-17 – A-21 |

### 3.5 Pengujian tambahan — 19 September 2026

Dijalankan setelah fitur penghapusan akun (SRS 1.3) dan pemakaian ulang serta arsip
inkubator (SRS 1.4) ditambahkan, dengan migrasi basis data `b5e2a7c9d314` terpasang.
Butir A-1 s.d. A-15 di atas tetap mencatat keadaan 7 September 2026.

| # | Butir | Hasil |
|---|---|---|
| A-16 | `user_delete_check.py` — penghapusan akun tanpa membuang catatannya (F-4.28) | **22/22 Lulus** |
| A-17 | `incubator_history_check.py` — satu inkubator dipakai dua bayi berturut-turut lalu diarsipkan: pemulangan menutup peringatan bayi, tampilan inkubator terbatas pada periode saat ini (termasuk putar ulang aliran langsung), riwayat sensor per bayi dari data mentah dan agregat per menit, bayi yang sudah pulang tetap dapat dicari dan dilaporkan, arsip hanya-baca, nomor tidak dipakai ulang, pemulihan | **78/78 Lulus** |
| A-18 | Enam suite A-1 s.d. A-6 dijalankan ulang setelah migrasi | **Seluruhnya Lulus** — 39/39, 30/30, firmware, 14/14, 28/28, 18/18 |
| A-19 | Build produksi dashboard (`next build`) | **Lulus** — 20 rute (bertambah `/babies` dan `/admin/incubators`), tanpa galat |
| A-20 | Basis data baru dari `schema.sql` dibandingkan dengan basis data hasil migrasi, untuk empat tabel yang berubah | **Lulus** — definisi, kekangan, dan indeks identik; hanya urutan kolom `archived_at` yang berbeda |
| A-21 | Penelusuran antarmuka dashboard melalui BFF (`:3000`) dengan peramban tanpa-kepala: memulangkan, mengarsipkan, dan memulihkan lewat tombolnya; Riwayat Bayi; laporan bayi yang sudah pulang; lebar layar 1280 px dan 390 px | **Lulus** — tanpa galat konsol, tanpa gulir menyamping |

---

## 4. Bagian B — Skenario UAT untuk Dijalankan Klien

**Belum dijalankan.** Kolom Hasil, Catatan, dan Tanggal diisi penguji saat pelaksanaan.

Dijalankan pada **server produksi**, dengan akun sungguhan, oleh pengguna dari peran yang
bersangkutan — bukan oleh Pengembang.

### 4.1 Umum

| # | Skenario | Langkah | Diharapkan | SRS | Hasil | Catatan |
|---|---|---|---|---|---|---|
| B-01 | Masuk sebagai perawat | Buka alamat sistem, isi email & kata sandi, tekan Masuk | Masuk ke dasbor, nama dan peran tampil di kanan atas | F-4.1 | | |
| B-02 | Masuk dengan kata sandi salah | Isi kata sandi keliru | Ditolak dengan pesan yang jelas; tidak masuk | F-4.5 | | |
| B-03 | Keluar | Tekan Keluar | Kembali ke halaman masuk; menekan tombol kembali peramban tidak membuka data | F-4.1 | | |
| B-04 | Batas peran perawat | Masuk sebagai perawat, buka alamat `/admin/users` langsung | Ditolak atau dialihkan; data pengguna tidak tampil | F-4.4 | | |
| B-05 | Batas peran dokter | Masuk sebagai dokter, buka `/admin/audit-logs` | Ditolak | F-4.4 | | |

### 4.2 Perawat

| # | Skenario | Langkah | Diharapkan | SRS | Hasil | Catatan |
|---|---|---|---|---|---|---|
| B-06 | Membaca dasbor | Buka dasbor | Jumlah total/terisi/kosong/warning/tidak tersedia sesuai keadaan bangsal | F-6.1 | | |
| B-07 | Mendaftarkan bayi | Daftar Bayi Baru, isi identitas, riwayat ibu, DPJP, pilih inkubator kosong | Tersimpan; inkubator berubah menjadi Terisi | F-4.6, F-4.7 | | |
| B-08 | Inkubator terisi tidak muncul | Ulangi pendaftaran, lihat pilihan inkubator | Inkubator yang baru terisi tidak muncul lagi | F-2.3 | | |
| B-09 | Membaca grafik | Buka detail inkubator yang alatnya mengirim | Grafik terisi; pita rentang normal tampak; nilai terakhir di kanan | F-6.4 | | |
| B-10 | Arti garis terputus | Lepas probe DS18B20 sekitar satu menit, amati grafik Suhu Bayi | Garis **terputus**, tidak turun ke nol | F-4.21, D-5 | | |
| B-11 | Mencatat monitoring | Detail bayi → Monitoring, isi, simpan | Tersimpan dan muncul di riwayat | F-4.10 | | |
| B-12 | Nilai vital terisi otomatis | Buka Monitoring pada inkubator yang alatnya aktif | Kolom vital terisi dari bacaan terakhir dan **dapat diubah** | F-4.11 | | |
| B-13 | Kolom kosong ≠ nol | Kosongkan Respiratory Rate, simpan, buka laporan | Tampil sebagai tidak diukur, bukan 0 | F-4.12, D-5 | | |
| B-14 | Mencatat Aksi | Detail bayi → Aksi, nilai 6 butir, simpan | Tersimpan; total maksimal 24 | F-4.13 | | |
| B-15 | Mencatat keterlibatan | Detail bayi → Keterlibatan, isi 6 butir + durasi | Tersimpan; total maksimal 24 | F-4.14 | | |
| B-16 | Mencatat observasi | Detail bayi → Observasi, isi butir | Tersimpan; total maksimal 168 | F-4.15 | | |
| B-17 | Unggah foto | Monitoring → lampirkan foto ≤ 5 MB | Terunggah dan tampil pada catatan | F-4.10 | | |
| B-18 | Memulangkan bayi | Lakukan pemulangan | Inkubator kembali Kosong; riwayat catatan tetap ada | F-4.8 | | |

### 4.3 Dokter

| # | Skenario | Langkah | Diharapkan | SRS | Hasil | Catatan |
|---|---|---|---|---|---|---|
| B-19 | Membaca data klinis | Buka bayi, lihat monitoring dan observasi | Seluruh catatan perawat terbaca | F-4.4 | | |
| B-20 | Menulis catatan dokter | Detail bayi → Catatan Dokter, tulis, simpan | Tersimpan dan tampil di ringkasan bayi | F-4.17 | | |
| B-21 | Perawat tidak bisa menulis catatan dokter | Masuk sebagai perawat, coba akses formulir catatan dokter | Tidak tersedia atau ditolak | F-4.17 | | |
| B-22 | Membuka laporan | Detail bayi → Laporan | Ringkasan lengkap: identitas, monitoring, observasi, keterlibatan, aksi, catatan dokter | F-4.26 | | |
| B-23 | Ekspor PDF | Tekan Export PDF | Berkas PDF terunduh dan dapat dibuka | F-4.27 | | |

### 4.4 Admin

| # | Skenario | Langkah | Diharapkan | SRS | Hasil | Catatan |
|---|---|---|---|---|---|---|
| B-24 | Menambah pengguna | Admin → Pengguna → tambah, pilih peran | Akun dapat dipakai masuk sesuai perannya | F-4.28 | | |
| B-25 | Menambah inkubator | Tambah Inkubator | Muncul di dasbor berstatus Kosong | F-4.29 | | |
| B-26 | Inkubator yang pernah dipakai tidak bisa dihapus | Buka inkubator kosong yang punya riwayat penempatan | Tombol **Hapus Inkubator** tidak tersedia; yang tersedia **Arsipkan Inkubator** (lihat B-53) | F-4.29 | | |
| B-27 | Memasang perangkat IoT | Detail Inkubator → Pasang Perangkat | Kunci ditampilkan **satu kali**; kartu berubah menjadi terpasang | F-4.30 | | |
| B-28 | Kunci tidak dapat dilihat ulang | Muat ulang halaman setelah B-27 | Kunci tidak ditampilkan lagi | F-4.30, NF-6 | | |
| B-29 | Mengubah ambang batas | Ubah batas atas Suhu Bayi menjadi lebih rendah dari suhu sekarang | Inkubator menjadi Warning dan peringatan tercatat | F-4.31, F-4.23 | | |
| B-30 | Mengembalikan ambang batas | Kembalikan ke nilai semula | Status kembali normal | F-4.31 | | |
| B-31 | Audit log | Admin → Audit Log | Perubahan pada B-24 s.d. B-29 tercatat lengkap dengan pelaku dan waktu | F-4.32 | | |

### 4.5 Perangkat IoT — pengujian ujung-ke-ujung

**Paling penting, dan satu-satunya yang belum pernah diuji terhadap server hidup.**

| # | Skenario | Langkah | Diharapkan | SRS | Hasil | Catatan |
|---|---|---|---|---|---|---|
| B-32 | Rig mengirim ke server | Program rig dengan kunci dari server produksi, nyalakan, buka serial monitor 115200 | Tampil `[POST] 201` berulang tiap ±3 detik | F-7.2, F-7.3 | | |
| B-33 | Data muncul di dasbor | Buka detail inkubator yang bersangkutan | Grafik terisi dalam waktu di bawah satu menit | F-6.4 | | |
| B-34 | Status perangkat daring | Lihat kartu Perangkat IoT | Berstatus **Online**, disertai alamat pengirim dan waktu kirim terakhir | F-6.5 | | |
| B-35 | Kunci salah ditolak | Program satu rig dengan kunci keliru | Serial menampilkan `[POST] 401`; tidak ada data masuk | F-4.18, NF-6 | | |
| B-36 | Backoff saat ditolak | Biarkan rig dari B-35 menyala satu menit | Jeda kirim melebar bertahap, tidak tetap 3 detik | F-7.6 | | |
| B-37 | Jaringan putus | Matikan WiFi, amati alat | Layar OLED tetap menampilkan nilai; serial menampilkan `-1` | F-7.5, F-7.7, NF-15 | | |
| B-38 | Jaringan pulih | Nyalakan kembali WiFi | Pengiriman berlanjut sendiri tanpa menyentuh alat | NF-15 | | |
| B-39 | Bayi berpindah inkubator | Pindahkan bayi lewat aplikasi, **tanpa** menyentuh alat | Pembacaan berikutnya tercatat atas nama bayi yang benar | F-4.20 | | |
| B-40 | Satu kunci satu inkubator | Coba pasang perangkat kedua pada inkubator yang sudah punya | Ditolak | F-2.4 | | |

### 4.6 Ketahanan dan operasional

| # | Skenario | Langkah | Diharapkan | SRS | Hasil | Catatan |
|---|---|---|---|---|---|---|
| B-41 | Nyala ulang server | `sudo reboot`, tunggu, buka dasbor | Seluruh layanan hidup sendiri tanpa campur tangan | F-3.2, NF-13 | | |
| B-42 | Data bertahan | Setelah B-41, periksa catatan yang dibuat sebelumnya | Seluruh data masih ada | NF-16 | | |
| B-43 | Pencadangan | Jalankan perintah pencadangan pada `DEPLOYMENT.md` | Berkas cadangan terbentuk dan tidak kosong | F-3.3 | | |
| B-44 | Aplikasi Android | Pasang APK, masuk, catat satu monitoring | Fungsi setara dashboard; data muncul di web | F-5.1 – F-5.3 | | |
| B-45 | Dua klien sinkron | Catat di Android, muat ulang dashboard web | Catatan tampil di kedua klien | F-5.1 | | |

### 4.7 Pemakaian ulang dan arsip inkubator

Jalankan berurutan pada satu inkubator yang alatnya mengirim data.

| # | Skenario | Langkah | Diharapkan | SRS | Hasil | Catatan |
|---|---|---|---|---|---|---|
| B-46 | Pemulangan menutup peringatan bayi | Biarkan satu peringatan aktif (mis. lepas probe SpO₂ setelah nilai rendah), lalu pulangkan bayinya; tunggu beberapa menit | Peringatan tercatat **ditutup saat bayi pulang**; inkubator tetap **Kosong** walau alat terus mengirim | F-4.8, F-4.36 | | |
| B-47 | Inkubator dipakai bayi berikutnya | Daftarkan bayi baru ke inkubator dari B-46, buka detailnya | Grafik dan Riwayat Peringatan hanya memuat periode bayi baru; keterangan *Sejak … masuk* tampil | F-4.34 | | |
| B-48 | Mencari bayi yang sudah pulang | Menu **Riwayat Bayi** → **Sudah Pulang**; cari nama atau No. Registrasi bayi dari B-46 | Bayi ditemukan, dengan tanggal masuk dan pulangnya | F-4.33, F-6.7 | | |
| B-49 | Laporan bayi yang sudah pulang | Buka bayi dari B-48 | Data Registrasi lengkap beserta Status dan Tanggal Pulang; Riwayat Data Sensor dan Riwayat Peringatan tampil; menu pencatatan tidak tampil | F-4.26, F-4.35, F-6.7 | | |
| B-50 | PDF bayi yang sudah pulang | Export PDF dari B-49 | Bagian Data Registrasi terisi, termasuk *Sudah pulang* dan tanggalnya — bukan tanda strip | F-4.26, F-4.27 | | |
| B-51 | Riwayat penggunaan inkubator | Buka detail inkubator dari B-47 | **Riwayat Penggunaan** memuat kedua bayi; nama bayi membuka laporannya | F-6.3 | | |
| B-52 | Menghapus inkubator yang belum pernah dipakai | Tambah Inkubator, buka, tekan **Hapus Inkubator** | Terhapus; tombol **Arsipkan** tidak muncul pada inkubator ini | F-4.29 | | |
| B-53 | Mengarsipkan inkubator | Pulangkan bayi dari B-47, lalu **Arsipkan Inkubator** | Hilang dari dasbor, ringkasan, dan pilihan pendaftaran; tampil di **Admin → Arsip Inkubator**; halamannya hanya-baca; kartu perangkat tidak tampil | F-4.37, F-6.8 | | |
| B-54 | Riwayat tetap utuh setelah arsip | Buka laporan kedua bayi lewat Riwayat Bayi | Riwayat sensor dan peringatan keduanya masih lengkap | F-4.35, D-8 | | |
| B-55 | Nomor tidak dipakai ulang | Setelah B-53, Tambah Inkubator | Mendapat nomor **setelah** nomor inkubator yang diarsipkan | F-4.37, D-8 | | |
| B-56 | Memulihkan inkubator | Arsip Inkubator → buka → **Pulihkan Inkubator** | Kembali ke dasbor berstatus **Tidak Tersedia**; setelah ditandai Kosong dapat dipilih lagi | F-4.37 | | |

---

## 5. Butir yang Belum Dapat Diuji

| Hal | Sebab | Tindakan |
|---|---|---|
| **HTTPS/TLS** (NF-12) | Membutuhkan nama domain; penerapan saat ini memakai alamat IP | Diuji bila domain tersedia; gunakan `STAGING=1` pada percobaan pertama |
| **Pengujian ujung-ke-ujung firmware** (B-32 – B-40) | Membutuhkan rig fisik dan server produksi secara bersamaan | Dijadwalkan bersama UAT |
| **Beban banyak inkubator** (NF-1) | Membutuhkan seluruh rig terpasang | Diuji setelah seluruh alat siap |
| **Python 3.12** | Seluruh pengujian berjalan pada Python 3.10 | Jalankan ulang Bagian A bila server memakai versi lain |

---

## 6. Kesimpulan Sementara

Seluruh **134 butir pengujian otomatis Bagian A lulus**, tanpa kegagalan. Pembangunan
dashboard, analisis statis aplikasi mobile, dan kompilasi firmware bersih. Pengujian
tambahan 19 September 2026 (§3.5) — penghapusan akun, pemakaian ulang dan arsip inkubator,
serta pengulangan seluruh suite setelah migrasi — juga lulus seluruhnya.

Bagian A membuktikan sistem **berfungsi sesuai rancangan pada lingkungan pengembangan**.
Bagian A **tidak** membuktikan sistem dapat diterima Klien — itu tugas Bagian B, yang belum
dijalankan.

Butir dengan risiko tertinggi adalah **B-32 sampai B-40**: rangkaian perangkat IoT terhadap
server produksi belum pernah diuji ujung-ke-ujung. Dianjurkan dijalankan lebih dahulu pada
sesi UAT, karena butir itu paling sulit didiagnosis dari jauh dan paling menentukan
kegunaan sistem sehari-hari.

---

## 7. Persetujuan

Diisi setelah Bagian B dijalankan.

| | Nama | Jabatan | Tanda tangan | Tanggal |
|---|---|---|---|---|
| Penguji (Klien) | | | | |
| Penanggung jawab bangsal | | | | |
| Pengembang | Sofyan Tandungan | Pengembang | | |

**Kesimpulan penerimaan** (lingkari salah satu):

- Diterima tanpa catatan
- Diterima dengan catatan — jumlah butir bercatatan: ____
- Belum diterima — jumlah butir gagal: ____

---

## Lampiran A — Catatan Insiden Selama Pengujian

Dicatat karena berdampak di luar pengujian ini.

**Berkas rusak pada `node_modules` dashboard (7 September 2026).**

Build produksi dashboard yang sebelumnya bersih tiba-tiba gagal dengan
`Module not found: next/font/google/target.css`. Penelusuran menemukan berkas
`node_modules/next/dist/server/capsize-font-metrics.json` (4,3 MB) tidak lagi berupa JSON
yang sah.

Kerusakannya **bukan** berkas terpotong — ukurannya utuh dan byte terakhirnya benar.
Yang terjadi adalah perubahan karakter di tengah berkas:

```
seharusnya:   "descent": -604,        "lineGap": 0,
menjadi:     `"de3cent": m604,        "l)neGap": 0,
```

`s`→`3`, `-`→`m`, `i`→`)`, spasi→backtick. Pola seperti ini lazimnya menunjukkan kerusakan
pada media penyimpanan atau memori, bukan kegagalan pengunduhan. Perlu dicatat pula bahwa
partisi C: mesin ini sempat terisi penuh hingga tersisa 318 MB pada 3 September, dan cache
npm berada di sana.

Dipulihkan dengan menghapus `node_modules/next` lalu memasangnya kembali; build kembali
menghasilkan 18 rute seperti baseline. **Tidak ada kode proyek yang terlibat.**

Disarankan: jalankan pemeriksaan kesehatan penyimpanan pada mesin pengembangan, dan pada
server produksi jalankan `npm ci` (bukan `npm install`) agar `node_modules` selalu dibangun
ulang dari lockfile.

## Lampiran B — Daftar Berkas Bukti

| Bukti | Lokasi |
|---|---|
| Suite pengujian | `backend/tests/*.py` |
| Kebutuhan berkode | `docs/deliverables/SRS.md` |
| Panduan penerapan | `DEPLOYMENT.md` |
| Panduan pengguna | `docs/MANUAL.md` |
| Referensi API | `docs/deliverables/api.html` |
