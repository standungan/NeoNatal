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
  created_at: string;
  updated_at: string;
  current_baby: CurrentBabySummary | null;
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
  age_in_days: number;
  parent: ParentInfo | null;
  maternal: MaternalRecord | null;
  current_assignment: AssignmentInfo | null;
  latest_vitals: MonitoringRecord | null;
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

export interface BabyReport {
  baby: BabyDetail;
  monitoring_history: MonitoringRecord[];
  involvement_history: InvolvementRecord[];
  involvement_summary: InvolvementSummary;
  generated_at: string;
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
