/**
 * Neonatal Care System — API types (copy-paste ready)
 * ----------------------------------------------------
 * One file you can drop into a frontend project. These mirror the FastAPI
 * request/response schemas exactly, as sent over the wire (snake_case).
 *
 * Convention:
 *   - `field: T`        → always present (required in requests / non-null in responses)
 *   - `field?: T`       → optional in a REQUEST body (may be omitted)
 *   - `field: T | null` → always present in a RESPONSE but may be null
 *
 * All `*_id` / id fields are UUID strings. All timestamps are ISO-8601 strings
 * (e.g. "2026-06-26T09:30:00+07:00"). Money/measure fields that are NUMERIC in
 * the DB arrive as JSON numbers.
 */

/* ============================================================
 * Enums / unions
 * ========================================================== */

export type Role = "admin" | "perawat" | "dokter";
export type Gender = "laki_laki" | "perempuan";
export type IncubatorStatus = "kosong" | "terisi" | "warning" | "tidak_tersedia";
export type VitalStatus = "normal" | "warning";
/** 5-band category (Indonesian labels) shared by the observation instrument and Pillar-6 involvement. */
export type InstrumentCategory =
  | "Sangat Baik"
  | "Baik"
  | "Cukup"
  | "Kurang"
  | "Sangat Kurang";

/* ============================================================
 * Auth
 * ========================================================== */

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  user_id: string;
  full_name: string;
  role: Role;
}

/** GET /auth/me */
export interface MeResponse {
  id: string;
  role: Role;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

/* ============================================================
 * Users (admin)
 * ========================================================== */

export interface UserCreateRequest {
  role: Role;
  email: string;
  password: string;
  full_name: string;
}

export interface UserUpdateRequest {
  full_name?: string;
  is_active?: boolean;
}

export interface PasswordResetRequest {
  new_password: string;
}

export interface UserResponse {
  id: string;
  role: Role;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

/* ============================================================
 * Incubators
 * ========================================================== */

export interface IncubatorCreateRequest {
  incubator_no: string;
  location?: string;
}

export interface IncubatorUpdateRequest {
  location?: string;
  status?: IncubatorStatus;
}

export interface IncubatorResponse {
  incubator_id: string;
  incubator_no: string;
  location: string | null;
  status: IncubatorStatus;
  created_at: string;
  updated_at: string;
}

export interface CurrentBabySummary {
  baby_id: string;
  baby_name: string;
  birth_date: string | null;
  assigned_at: string;
}

/** GET /incubators and /incubators/{id} */
export interface IncubatorDetailResponse extends IncubatorResponse {
  current_baby: CurrentBabySummary | null;
}

/* ============================================================
 * Babies + parents + assignment
 * ========================================================== */

export interface ParentRequest {
  mother_name?: string;
  father_name?: string;
  mother_phone?: string;
  mother_medical_history?: string;
  birth_history?: string;
  delivery_history?: string;
  additional_notes?: string;
}

export interface BabyCreateRequest {
  baby_name: string;
  gender: Gender;
  birth_date: string; // "YYYY-MM-DD"
  birth_weight?: number; // grams
  birth_length?: number; // cm
  gestational_age?: number; // weeks
  birth_type?: string;
  clinical_notes?: string;
  parent: ParentRequest; // object required; all its fields optional
  incubator_id: string; // must be a "kosong" incubator
}

export interface BabyUpdateRequest {
  baby_name?: string;
  clinical_notes?: string;
  birth_weight?: number;
}

export interface ParentResponse {
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

export interface BabyResponse {
  baby_id: string;
  baby_name: string;
  gender: Gender;
  birth_date: string;
  birth_weight: number | null;
  birth_length: number | null;
  gestational_age: number | null;
  birth_type: string | null;
  clinical_notes: string | null;
  is_active: boolean;
  created_at: string;
}

/** Returned by GET /babies/{id}, POST /babies, PUT /babies/{id} */
export interface BabyDetailResponse extends BabyResponse {
  age_in_days: number;
  parent: ParentResponse | null;
  current_assignment: AssignmentInfo | null;
  latest_vitals: MonitoringResponse | null;
}

/* ============================================================
 * Monitoring (vitals + comfort scores)
 * ========================================================== */

export interface MonitoringCreateRequest {
  observation_time: string; // required
  suhu_bayi?: number; // °C
  suhu_inkubator?: number; // °C
  kelembapan_inkubator?: number; // % RH
  heart_rate?: number; // bpm
  respiratory_rate?: number; // breaths/min
  spo2?: number; // %
  expression_score?: number; // 1–5
  movement_score?: number; // 1–5
  pain_score?: number; // 0–7 (NIPS)
  sleep_duration_min?: number; // minutes
  sleep_quality?: number; // 1–5
  agitation_episodes?: number; // count
  catatan?: string;
}

export interface MonitoringResponse {
  monitoring_id: string;
  baby_id: string;
  recorded_by: string;
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
  /** Derived from thresholds on each read — never sent in the request. */
  vital_status: VitalStatus;
  created_at: string;
}

export interface PhotoUploadResponse {
  monitoring_id: string;
  foto_url: string;
}

/* ============================================================
 * Parent involvement — Pillar 6 "Kerjasama dengan Keluarga"
 * 6 items, each scored 0–3. GET /involvement/catalog for the items.
 * ========================================================== */

/** GET /api/v1/involvement/catalog */
export interface InvolvementCatalogItem {
  item_code: string; // "keluarga_1".."keluarga_6"
  text: string;
}
export interface InvolvementCatalog {
  key: string;   // "keluarga"
  label: string; // "Kerjasama dengan Keluarga"
  items: InvolvementCatalogItem[];
  total_items: number; // 6
  max_total: number;   // 18
}

export interface InvolvementCreateRequest {
  observation_time: string; // required
  /** { item_code: 0..3 }, e.g. { keluarga_1: 3, keluarga_2: 2, ... }. Omitted items count as 0. */
  scores: Record<string, number>; // required
  catatan?: string;
  durasi_menyusui?: number; // minutes (informational)
  durasi_interaksi?: number; // minutes (informational)
  kondisi_bayi?: string;
}

/** Per-item breakdown (returned; drives the radar/bars). */
export interface InvolvementItemScore {
  item_code: string;
  text: string;
  score: number; // 0–3
  max: number; // 3
  percentage: number; // 0–100
}

/** An item scored 0 or 1 → flagged for attention. */
export interface InvolvementAlarm {
  item_code: string;
  text: string;
  score: number; // 0 or 1
}

export interface InvolvementResponse {
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
  total_score: number; // 0–18
  max_total: number; // 18
  percentage: number; // 0–100
  category: InstrumentCategory | null;
  items: InvolvementItemScore[];
  alarms: InvolvementAlarm[];
  created_at: string;
}

export interface InvolvementSummaryResponse {
  total_sessions: number;
  avg_percentage: number | null;
  latest_percentage: number | null;
  latest_category: InstrumentCategory | null;
  avg_durasi_menyusui: number | null;
  avg_durasi_interaksi: number | null;
}

/* ============================================================
 * Observation (Monitoring Bayi) — premature-baby instrument
 * Currently 6 pillars / 42 items, each scored 0–3.
 * GET /observation/catalog for the pillars & items.
 * ========================================================== */

/** GET /api/v1/observation/catalog */
export interface ObservationCatalogItem {
  item_code: string; // "{pillar_key}_{n}", e.g. "tidur_1"
  text: string;
}
export interface ObservationCatalogPillar {
  key: string; // "tidur", "nyeri", ...
  label: string;
  items: ObservationCatalogItem[];
}
export interface ObservationCatalog {
  pillars: ObservationCatalogPillar[];
  total_items: number; // 42
  max_total: number; // 126
}

export interface ObservationCreateRequest {
  observation_time: string; // required
  /** { item_code: 0..3 }. Omitted items count as 0. */
  scores: Record<string, number>; // required
  catatan?: string;
}

/** Per-pillar roll-up (returned; drives the radar). */
export interface ObservationPillarScore {
  key: string;
  label: string;
  score: number; // raw sum for the pillar
  max: number; // item_count * 3
  percentage: number; // 0–100
}

/** An item scored 0 or 1. A score of 0 also flips the incubator to "warning". */
export interface ObservationAlarm {
  item_code: string;
  text: string;
  pillar_label: string;
  score: number; // 0 or 1
}

export interface ObservationResponse {
  observation_id: string;
  baby_id: string;
  recorded_by: string;
  recorder_name: string | null;
  observation_time: string;
  scores: Record<string, number>;
  catatan: string | null;
  total_score: number; // 0–126
  max_total: number; // 126
  percentage: number; // 0–100
  category: InstrumentCategory | null;
  pillars: ObservationPillarScore[];
  alarms: ObservationAlarm[];
  created_at: string;
}

/* ============================================================
 * Menu Aksi — Pillar 8 "Kolaborasi Interprofesional"
 * 6 items, each scored 0–3 (pulled out of Monitoring Bayi).
 * GET /aksi/catalog for the items.
 * ========================================================== */

/** GET /api/v1/aksi/catalog */
export interface AksiCatalogItem {
  item_code: string; // "kolaborasi_1".."kolaborasi_6"
  text: string;
}
export interface AksiCatalog {
  key: string; // "kolaborasi"
  label: string; // "Kolaborasi Interprofesional"
  items: AksiCatalogItem[];
  total_items: number; // 6
  max_total: number; // 18
}

export interface AksiCreateRequest {
  observation_time: string; // required
  /** { item_code: 0..3 }. Omitted items count as 0. */
  scores: Record<string, number>; // required
  catatan?: string;
}

/** Per-item breakdown (returned; drives the radar & bars). */
export interface AksiItemScore {
  item_code: string;
  text: string;
  score: number; // 0–3
  max: number; // 3
  percentage: number; // 0–100
}

/** An item scored 0 or 1 (no incubator side effect). */
export interface AksiAlarm {
  item_code: string;
  text: string;
  score: number; // 0 or 1
}

export interface AksiResponse {
  aksi_id: string;
  baby_id: string;
  recorded_by: string;
  recorder_name: string | null;
  observation_time: string;
  scores: Record<string, number>;
  catatan: string | null;
  total_score: number; // 0–18
  max_total: number; // 18
  percentage: number; // 0–100
  category: InstrumentCategory | null;
  items: AksiItemScore[];
  alarms: AksiAlarm[];
  created_at: string;
}

/** GET /api/v1/babies/{id}/aksi/summary */
export interface AksiSummary {
  total_sessions: number;
  avg_percentage: number | null;
  latest_percentage: number | null;
  latest_category: InstrumentCategory | null;
}

/* ============================================================
 * Dashboard
 * ========================================================== */

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
  vital_status: VitalStatus;
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

/* ============================================================
 * Reports
 * ========================================================== */

export interface BabyReportResponse {
  baby: BabyDetailResponse;
  monitoring_history: MonitoringResponse[];
  involvement_history: InvolvementResponse[];
  involvement_summary: InvolvementSummaryResponse;
  generated_at: string;
}

/* ============================================================
 * Audit logs (admin)
 * ========================================================== */

export interface AuditLogResponse {
  log_id: string;
  user_id: string | null;
  user_name: string | null;
  action: string; // "LOGIN" | "CREATE" | "UPDATE" | "DISCHARGE" | "UPLOAD_PHOTO" | ...
  table_name: string | null;
  record_id: string | null;
  ip_address: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

/* ============================================================
 * Error envelope (FastAPI)
 * ========================================================== */

/** Body of any 4xx/5xx response. `detail` is a string for app errors, or an
 *  array of field errors for 422 validation failures. */
export interface ApiError {
  detail:
    | string
    | Array<{ loc: (string | number)[]; msg: string; type: string }>;
}
