// Mirrors the FastAPI response schemas (snake_case as sent over the wire).

export type Role = "admin" | "perawat" | "dokter";

export interface AuthUser {
  user_id: string;
  full_name: string;
  role: Role;
}

export interface MeResponse {
  id: string;
  role: Role;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export type IncubatorStatus = "kosong" | "terisi" | "warning" | "tidak_tersedia";

export interface DashboardStats {
  total: number;
  terisi: number;
  kosong: number;
  warning: number;
  tidak_tersedia: number;
}

export interface BabySummary {
  baby_id: string;
  baby_name: string;
  age_in_days: number;
  birth_weight: number | null;
  assigned_at: string;
}

export interface LatestVitals {
  suhu_bayi: number | null;
  heart_rate: number | null;
  spo2: number | null;
  observation_time: string;
  vital_status: "normal" | "warning";
}

export interface IncubatorDashboardItem {
  incubator_id: string;
  incubator_no: string;
  location: string | null;
  status: IncubatorStatus;
  current_baby: BabySummary | null;
  latest_vitals: LatestVitals | null;
  /** An IoT sensor unit is bound to this incubator. */
  has_device: boolean;
  /** Last telemetry POST. null = device installed but has never reported. */
  device_last_seen_at: string | null;
  /**
   * Recent skin-temperature samples, oldest first. Nulls are kept in place so
   * the trace can break where the sensor reported nothing.
   */
  sparkline: (number | null)[];
}

export interface DashboardResponse {
  stats: DashboardStats;
  incubators: IncubatorDashboardItem[];
}

export interface CurrentBabySummary {
  baby_id: string;
  baby_name: string;
  birth_date: string | null;
  assigned_at: string;
}

export interface IncubatorDetail {
  incubator_id: string;
  incubator_no: string;
  location: string | null;
  status: IncubatorStatus;
  /** Set once retired: read-only, hidden from the dashboard and admission. */
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  current_baby: CurrentBabySummary | null;
  /** Has any baby ever been placed here? Unused → deletable; used → archive only. */
  has_history: boolean;
}

/** One baby's stay in an incubator — a row of the incubator's usage history. */
export interface IncubatorPlacement {
  assignment_id: string;
  baby_id: string;
  baby_name: string;
  no_registrasi_nicu: string | null;
  status: "active" | "discharged";
  assigned_at: string;
  discharged_at: string | null;
  assigned_by_name: string | null;
  dpjp_name: string | null;
}

export interface MonitoringRecord {
  monitoring_id: string;
  baby_id: string;
  recorder_name: string | null;
  observation_time: string;
  suhu_bayi: number | null;
  suhu_inkubator: number | null;
  kelembapan_inkubator: number | null;
  heart_rate: number | null;
  respiratory_rate: number | null;
  spo2: number | null;
  expression_score: number | null;
  movement_score: number | null;
  pain_score: number | null;
  sleep_duration_min: number | null;
  sleep_quality: number | null;
  agitation_episodes: number | null;
  catatan: string | null;
  foto_url: string | null;
  vital_status: "normal" | "warning";
  created_at: string;
}

export interface ParentInfo {
  parent_id: string;
  mother_name: string | null;
  father_name: string | null;
  mother_phone: string | null;
  mother_medical_history: string | null;
  birth_history: string | null;
  delivery_history: string | null;
  additional_notes: string | null;
}

export interface AssignmentInfo {
  assignment_id: string;
  incubator_id: string;
  incubator_no: string;
  location: string | null;
  assigned_at: string;
  status: "active" | "discharged";
  discharged_at: string | null;
  assigned_by_name: string | null;
  // registration data (updates02)
  no_registrasi_nicu: string | null;
  rumah_sakit: string | null;
  ruang_nicu: string | null;
  dpjp_name: string | null;
}

export interface MaternalRecord {
  maternal_record_id: string;
  no_rm_ibu: string | null;
  umur_ibu: number | null;
  pendidikan: string | null;
  pekerjaan: string | null;
  alamat: string | null;
  golongan_darah: string | null;
  kehamilan_ke: number | null;
  jumlah_persalinan_hidup: number | null;
  riwayat_abortus: boolean | null;
  riwayat_prematur: boolean | null;
  riwayat_bblr: boolean | null;
  riwayat_bayi_meninggal: boolean | null;
  usia_kehamilan_lahir: number | null;
  jenis_kehamilan: string | null;
  anc_rutin: boolean | null;
  jumlah_anc: number | null;
  hipertensi_kehamilan: boolean | null;
  preeklamsia: boolean | null;
  diabetes_gestasional: boolean | null;
  infeksi_hamil: boolean | null;
  perdarahan_hamil: boolean | null;
  ketuban_pecah_dini: boolean | null;
  merokok: boolean | null;
  paparan_asap_rokok: boolean | null;
  konsumsi_alkohol: boolean | null;
  obat_tertentu: boolean | null;
  obat_tertentu_ket: string | null;
  tanggal_persalinan: string | null;
  jenis_persalinan: string | null;
  tempat_persalinan: string | null;
  indikasi_prematur: string[] | null;
  indikasi_prematur_lainnya: string | null;
  komplikasi_persalinan: string[] | null;
  komplikasi_lainnya: string | null;
  apgar_menit_1: number | null;
  apgar_menit_5: number | null;
  kondisi_umum: string | null;
  masih_dirawat: boolean | null;
  komplikasi_postpartum: boolean | null;
  dapat_berjalan: boolean | null;
  dapat_menyusui: boolean | null;
}

export interface BabyDetail {
  baby_id: string;
  baby_name: string;
  gender: "laki_laki" | "perempuan";
  birth_date: string;
  birth_weight: number | null;
  birth_length: number | null;
  gestational_age: number | null;
  birth_type: string | null;
  clinical_notes: string | null;
  // extended identity (updates02)
  no_rm_bayi: string | null;
  jam_lahir: string | null;
  usia_masuk_nicu_jam: number | null;
  lingkar_kepala: number | null;
  lingkar_dada: number | null;
  golongan_darah: string | null;
  /** false once discharged */
  is_active: boolean;
  age_in_days: number;
  parent: ParentInfo | null;
  maternal: MaternalRecord | null;
  /** Only while the baby is in an incubator; null after discharge. */
  current_assignment: AssignmentInfo | null;
  /** Every placement, newest first — discharged ones included. */
  placements: AssignmentInfo[];
  latest_vitals: MonitoringRecord | null;
}

/** A row of the baby list (GET /babies): identity + most recent placement. */
export interface BabyListItem {
  baby_id: string;
  baby_name: string;
  gender: "laki_laki" | "perempuan";
  birth_date: string;
  no_rm_bayi: string | null;
  is_active: boolean;
  created_at: string;
  placement: AssignmentInfo | null;
}

/** The placement a baby's pages should describe: the current one, else the last. */
export function latestPlacement(baby: Pick<BabyDetail, "current_assignment" | "placements">): AssignmentInfo | null {
  return baby.current_assignment ?? baby.placements[0] ?? null;
}

export interface InvolvementSummary {
  total_sessions: number;
  avg_percentage: number | null;
  latest_percentage: number | null;
  latest_category: string | null;
  avg_durasi_menyusui: number | null;
  avg_durasi_interaksi: number | null;
}

// ── Keterlibatan Orang Tua — Pilar 6 "Kerjasama dengan Keluarga" ─────────────

export interface InvolvementCatalogItem {
  item_code: string;
  text: string;
}

export interface InvolvementCatalog {
  key: string;
  label: string;
  items: InvolvementCatalogItem[];
  total_items: number;
  max_total: number;
}

export interface InvolvementItemScore {
  item_code: string;
  text: string;
  score: number;
  max: number;
  percentage: number;
}

export interface InvolvementAlarm {
  item_code: string;
  text: string;
  score: number;
}

export interface InvolvementRecord {
  involvement_id: string;
  baby_id: string;
  recorded_by: string;
  recorder_name: string | null;
  observation_time: string;
  scores: Record<string, number>;
  catatan: string | null;
  durasi_menyusui: number | null;
  durasi_interaksi: number | null;
  kondisi_bayi: string | null;
  total_score: number;
  max_total: number;
  percentage: number;
  category: string | null;
  items: InvolvementItemScore[];
  alarms: InvolvementAlarm[];
  created_at: string;
}

export interface DoctorNote {
  note_id: string;
  baby_id: string;
  recorded_by: string;
  recorder_name: string | null;
  observation_time: string;
  catatan: string;
  created_at: string;
}

export interface BabyReport {
  baby: BabyDetail;
  monitoring_history: MonitoringRecord[];
  involvement_history: InvolvementRecord[];
  involvement_summary: InvolvementSummary;
  doctor_note_latest: DoctorNote | null;
  generated_at: string;
}

// ── Per-incubator sensor alert thresholds (admin) ────────────────────────────

export interface ThresholdMetric {
  key: string;
  label: string;
  unit: string;
  min: number | null;
  max: number | null;
}

export interface IncubatorThresholds {
  incubator_id: string;
  incubator_no: string;
  is_custom: boolean;
  metrics: ThresholdMetric[];
}

// ── Observasi 8 Pilar ───────────────────────────────────────────────────────

export interface ObservationCatalogItem {
  item_code: string;
  text: string;
}

export interface ObservationCatalogPillar {
  key: string;
  label: string;
  items: ObservationCatalogItem[];
}

export interface ObservationCatalog {
  pillars: ObservationCatalogPillar[];
  total_items: number;
  max_total: number;
}

export interface ObservationPillarScore {
  key: string;
  label: string;
  score: number;
  max: number;
  percentage: number;
}

export interface ObservationAlarm {
  item_code: string;
  text: string;
  pillar_label: string;
  score: number;
}

export interface ObservationRecord {
  observation_id: string;
  baby_id: string;
  recorded_by: string;
  recorder_name: string | null;
  observation_time: string;
  scores: Record<string, number>;
  catatan: string | null;
  total_score: number;
  max_total: number;
  percentage: number;
  category: string | null;
  pillars: ObservationPillarScore[];
  alarms: ObservationAlarm[];
  created_at: string;
}

// ── Menu Aksi — Pilar 8 "Kolaborasi Interprofesional" ───────────────────────

export interface AksiCatalogItem {
  item_code: string;
  text: string;
}

export interface AksiCatalog {
  key: string;
  label: string;
  items: AksiCatalogItem[];
  total_items: number;
  max_total: number;
}

export interface AksiItemScore {
  item_code: string;
  text: string;
  score: number;
  max: number;
  percentage: number;
}

export interface AksiAlarm {
  item_code: string;
  text: string;
  score: number;
}

export interface AksiRecord {
  aksi_id: string;
  baby_id: string;
  recorded_by: string;
  recorder_name: string | null;
  observation_time: string;
  scores: Record<string, number>;
  catatan: string | null;
  total_score: number;
  max_total: number;
  percentage: number;
  category: string | null;
  items: AksiItemScore[];
  alarms: AksiAlarm[];
  created_at: string;
}

export interface ManagedUser {
  id: string;
  role: Role;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface AuditLog {
  log_id: string;
  user_id: string | null;
  user_name: string | null;
  action: string;
  table_name: string | null;
  record_id: string | null;
  ip_address: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

// ── IoT device (updates03) ───────────────────────────────────────────────────

export interface Device {
  device_id: string;
  incubator_id: string | null;
  label: string | null;
  firmware_version: string | null;
  last_seen_at: string | null;
  /** Where the last reading came from. Provenance only — never identity. */
  last_ip: string | null;
  /** Optional single IP or CIDR permitted on the unauthenticated legacy route. */
  allowed_ip: string | null;
  is_active: boolean;
  created_at: string;
}

/**
 * Only ever returned by POST /incubators/{id}/device. `device_key` is the
 * plaintext key, and this is the single moment it exists anywhere outside the
 * firmware — the server stores only its SHA-256.
 */
export interface DeviceProvisionResponse extends Device {
  device_key: string;
}

/**
 * A device is considered online if it reported within this window. It POSTs
 * every 3s, so this is generous enough to absorb a missed beat or two plus the
 * dashboard's own poll latency, without a healthy rig flickering offline.
 */
export const DEVICE_ONLINE_WINDOW_MS = 30_000;

export function isDeviceOnline(lastSeenAt: string | null | undefined): boolean {
  if (!lastSeenAt) return false;
  return Date.now() - new Date(lastSeenAt).getTime() < DEVICE_ONLINE_WINDOW_MS;
}

/**
 * One stored sample. Every metric is nullable and null is meaningful: the
 * sensor had nothing to report (probe off the baby, DHT22 read failure), which
 * is NOT the same as zero. Charts must break the line, never plot a 0.
 */
export interface SensorReading {
  reading_id: string;
  incubator_id: string;
  baby_id: string | null;
  recorded_at: string;
  suhu_bayi: number | null;
  suhu_inkubator: number | null;
  kelembapan_inkubator: number | null;
  heart_rate: number | null;
  spo2: number | null;
  respiratory_rate: number | null;
  source: "sensor" | "simulator";
}

/**
 * One alert episode raised by the IoT threshold engine.
 *
 * `value`/`threshold` are frozen at the moment it opened, so the entry still
 * reads correctly after an admin edits the incubator's thresholds.
 * Acknowledging is not resolving: `resolved_at` is set by readings, never by a click.
 */
export interface SensorAlert {
  alert_id: string;
  incubator_id: string;
  baby_id: string | null;
  baby_name: string | null;
  alert_type:
    | "desaturation"
    | "bradycardia"
    | "tachycardia"
    | "temp_out_of_range";
  metric_key: string;
  severity: "warning" | "critical";
  value: number | null;
  threshold: number | null;
  started_at: string;
  resolved_at: string | null;
  /**
   * null = readings came back in range. "discharged"/"archived" = closed because
   * the baby went home or the incubator was retired — not a recovery.
   */
  resolved_reason: "discharged" | "archived" | null;
  acknowledged_by: string | null;
  acknowledged_by_name: string | null;
  acknowledged_at: string | null;
  /** Filled on a baby's alert list, where the incubator is not otherwise shown. */
  incubator_no: string | null;
}

/** One bucket of a baby's sensor history: mean plus the extremes inside it. */
export interface SensorHistoryPoint {
  t: string;
  samples: number;
  suhu_bayi: number | null;
  suhu_bayi_min: number | null;
  suhu_bayi_max: number | null;
  suhu_inkubator: number | null;
  suhu_inkubator_min: number | null;
  suhu_inkubator_max: number | null;
  kelembapan_inkubator: number | null;
  kelembapan_inkubator_min: number | null;
  kelembapan_inkubator_max: number | null;
  heart_rate: number | null;
  heart_rate_min: number | null;
  heart_rate_max: number | null;
  spo2: number | null;
  spo2_min: number | null;
  spo2_max: number | null;
}

export interface BabySensorHistory {
  bucket_minutes: number;
  points: SensorHistoryPoint[];
}

export const ALERT_LABELS: Record<SensorAlert["alert_type"], string> = {
  desaturation: "Saturasi turun",
  bradycardia: "Bradikardia",
  tachycardia: "Takikardia",
  temp_out_of_range: "Suhu di luar batas",
};
