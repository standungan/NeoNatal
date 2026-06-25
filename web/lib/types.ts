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
  age_in_days: number;
  parent: ParentInfo | null;
  current_assignment: AssignmentInfo | null;
  latest_vitals: MonitoringRecord | null;
}

export interface InvolvementSummary {
  total_sessions: number;
  avg_skor: number | null;
  avg_durasi_menyusui: number | null;
  avg_durasi_interaksi: number | null;
  latest_skor: number | null;
  latest_kategori: string | null;
}

export interface InvolvementRecord {
  involvement_id: string;
  baby_id: string;
  recorder_name: string | null;
  observation_time: string;
  durasi_menyusui: number | null;
  durasi_interaksi: number | null;
  // Pillar 8 sub-domains (0–4 each)
  presence_score: number | null;
  physical_interaction_score: number | null;
  feeding_participation_score: number | null;
  care_participation_score: number | null;
  knowledge_score: number | null;
  communication_score: number | null;
  emotional_readiness_score: number | null;
  discharge_readiness_score: number | null;
  catatan: string | null;
  skor_keterlibatan: number | null;
  skor_kategori: string | null;
  kondisi_bayi: string | null;
  created_at: string;
}

export interface BabyReport {
  baby: BabyDetail;
  monitoring_history: MonitoringRecord[];
  involvement_history: InvolvementRecord[];
  involvement_summary: InvolvementSummary;
  generated_at: string;
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
