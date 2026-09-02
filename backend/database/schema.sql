-- =============================================================================
-- Sistem Monitoring Bayi pada Inkubator
-- PostgreSQL DDL — schema.sql
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- ENUMS
-- =============================================================================

CREATE TYPE user_role AS ENUM ('admin', 'perawat', 'dokter');

CREATE TYPE incubator_status AS ENUM ('kosong', 'terisi', 'warning', 'tidak_tersedia');

CREATE TYPE assignment_status AS ENUM ('active', 'discharged');

CREATE TYPE gender_type AS ENUM ('laki_laki', 'perempuan');

-- updates02 — expanded NICU intake / maternal record
CREATE TYPE blood_type AS ENUM ('A', 'B', 'AB', 'O');
CREATE TYPE pendidikan_type AS ENUM ('tidak_sekolah', 'sd', 'smp', 'sma', 'diploma', 's1', 's2', 's3');
CREATE TYPE jenis_persalinan AS ENUM ('normal', 'sc', 'vakum', 'forceps');
CREATE TYPE kondisi_umum AS ENUM ('baik', 'cukup', 'buruk');
CREATE TYPE jenis_kehamilan AS ENUM ('tunggal', 'kembar');

-- updates03 — IoT telemetry provenance
CREATE TYPE sensor_source AS ENUM ('sensor', 'simulator');

-- updates03 P4 — only alert types a real sensor can raise. apnea/door_open/
-- environment need hardware that does not exist, and a type nothing can emit is
-- dead schema.
CREATE TYPE sensor_alert_type AS ENUM
    ('desaturation', 'bradycardia', 'tachycardia', 'temp_out_of_range');
CREATE TYPE sensor_alert_severity AS ENUM ('warning', 'critical');

-- =============================================================================
-- TABLE: users
-- =============================================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role            user_role NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: incubators
-- =============================================================================

CREATE TABLE incubators (
    incubator_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incubator_no    VARCHAR(10) NOT NULL UNIQUE,
    location        VARCHAR(255),
    status          incubator_status NOT NULL DEFAULT 'kosong',
    alert_thresholds JSONB,                                  -- admin-set sensor min/max; NULL = code defaults
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: babies
-- =============================================================================

CREATE TABLE babies (
    baby_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baby_name           VARCHAR(255) NOT NULL,
    gender              gender_type NOT NULL,
    birth_date          DATE NOT NULL,
    birth_weight        NUMERIC(6, 2),       -- grams, e.g. 2400.00
    birth_length        NUMERIC(5, 1),       -- cm
    gestational_age     SMALLINT,            -- weeks
    birth_type          VARCHAR(100),        -- jenis kelahiran
    clinical_notes      TEXT,
    -- extended identity (updates02)
    no_rm_bayi          VARCHAR(50),
    jam_lahir           TIME,
    usia_masuk_nicu_jam SMALLINT,            -- hours
    lingkar_kepala      NUMERIC(4, 1),       -- cm
    lingkar_dada        NUMERIC(4, 1),       -- cm
    golongan_darah      blood_type,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: parents
-- One-to-one with babies — each registered baby has exactly one parent record
-- =============================================================================

CREATE TABLE parents (
    parent_id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baby_id                 UUID NOT NULL UNIQUE REFERENCES babies(baby_id) ON DELETE CASCADE,
    mother_name             VARCHAR(255),
    father_name             VARCHAR(255),
    mother_phone            VARCHAR(20),
    mother_medical_history  TEXT,
    birth_history           TEXT,
    delivery_history        TEXT,
    additional_notes        TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: maternal_records  (updates02 — Rekam Jejak Ibu Bayi)
-- One-to-one with babies. Mother name/phone stay in parents; this holds the
-- structured obstetric / pregnancy / delivery record. All fields optional.
-- =============================================================================

CREATE TABLE maternal_records (
    maternal_record_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baby_id                 UUID NOT NULL UNIQUE REFERENCES babies(baby_id) ON DELETE CASCADE,
    -- A. identitas ibu
    no_rm_ibu               VARCHAR(50),
    umur_ibu                SMALLINT,
    pendidikan              pendidikan_type,
    pekerjaan               VARCHAR(100),
    alamat                  TEXT,
    golongan_darah          blood_type,
    -- B. riwayat obstetri
    kehamilan_ke            SMALLINT,
    jumlah_persalinan_hidup SMALLINT,
    riwayat_abortus         BOOLEAN,
    riwayat_prematur        BOOLEAN,
    riwayat_bblr            BOOLEAN,
    riwayat_bayi_meninggal  BOOLEAN,
    -- C. riwayat kehamilan saat ini
    usia_kehamilan_lahir    SMALLINT,
    jenis_kehamilan         jenis_kehamilan,
    anc_rutin               BOOLEAN,
    jumlah_anc              SMALLINT,
    hipertensi_kehamilan    BOOLEAN,
    preeklamsia             BOOLEAN,
    diabetes_gestasional    BOOLEAN,
    infeksi_hamil           BOOLEAN,
    perdarahan_hamil        BOOLEAN,
    ketuban_pecah_dini      BOOLEAN,
    merokok                 BOOLEAN,
    paparan_asap_rokok      BOOLEAN,
    konsumsi_alkohol        BOOLEAN,
    obat_tertentu           BOOLEAN,
    obat_tertentu_ket       TEXT,
    -- D. riwayat persalinan
    tanggal_persalinan      DATE,
    jenis_persalinan        jenis_persalinan,
    tempat_persalinan       VARCHAR(150),
    indikasi_prematur       JSONB,           -- list[str]
    indikasi_prematur_lainnya TEXT,
    komplikasi_persalinan   JSONB,           -- list[str]
    komplikasi_lainnya      TEXT,
    apgar_menit_1           SMALLINT,
    apgar_menit_5           SMALLINT,
    -- E. kondisi ibu setelah melahirkan
    kondisi_umum            kondisi_umum,
    masih_dirawat           BOOLEAN,
    komplikasi_postpartum   BOOLEAN,
    dapat_berjalan          BOOLEAN,
    dapat_menyusui          BOOLEAN,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: baby_incubator_assignments
-- Tracks which baby is/was in which incubator, with full history
-- =============================================================================

CREATE TABLE baby_incubator_assignments (
    assignment_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baby_id             UUID NOT NULL REFERENCES babies(baby_id),
    incubator_id        UUID NOT NULL REFERENCES incubators(incubator_id),
    assigned_by         UUID NOT NULL REFERENCES users(id),   -- perawat penerima
    assigned_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),   -- tanggal masuk NICU
    discharged_at       TIMESTAMPTZ,
    status              assignment_status NOT NULL DEFAULT 'active',
    -- registration data (updates02)
    no_registrasi_nicu  VARCHAR(30) UNIQUE,                   -- auto: NICU-<year>-<0001…>
    rumah_sakit         VARCHAR(150),
    ruang_nicu          VARCHAR(100),
    dpjp_id             UUID REFERENCES users(id)             -- dokter penanggung jawab
);

-- Only one active assignment per incubator at a time
CREATE UNIQUE INDEX uq_active_incubator_assignment
    ON baby_incubator_assignments (incubator_id)
    WHERE status = 'active';

-- Only one active assignment per baby at a time
CREATE UNIQUE INDEX uq_active_baby_assignment
    ON baby_incubator_assignments (baby_id)
    WHERE status = 'active';

-- =============================================================================
-- TABLE: monitoring_records
-- Each record = one nurse observation session for a baby
-- =============================================================================

CREATE TABLE monitoring_records (
    monitoring_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baby_id             UUID NOT NULL REFERENCES babies(baby_id),
    recorded_by         UUID NOT NULL REFERENCES users(id),
    observation_time    TIMESTAMPTZ NOT NULL,
    suhu_bayi           NUMERIC(4, 1),       -- °C, e.g. 36.8
    suhu_inkubator      NUMERIC(4, 1),       -- °C, e.g. 33.5
    kelembapan_inkubator NUMERIC(5, 2),      -- % RH (Pillar 7), e.g. 55.00
    heart_rate          SMALLINT,            -- bpm
    respiratory_rate    SMALLINT,            -- breaths/min (Pillar 1), normal 40–60
    spo2                NUMERIC(5, 2),       -- %, e.g. 98.00
    expression_score    SMALLINT CHECK (expression_score BETWEEN 1 AND 5),
    movement_score      SMALLINT CHECK (movement_score BETWEEN 1 AND 5),
    pain_score          SMALLINT CHECK (pain_score BETWEEN 0 AND 7),    -- Pillar 6 (NIPS), >=4 = pain
    sleep_duration_min  SMALLINT,            -- Pillar 5, minutes
    sleep_quality       SMALLINT CHECK (sleep_quality BETWEEN 1 AND 5), -- Pillar 5
    agitation_episodes  SMALLINT,            -- Pillar 5, count
    catatan             TEXT,
    foto_url            VARCHAR(500),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: parent_involvement_records
-- Keterlibatan Orang Tua = PILAR 6 "Kerjasama dengan Keluarga" (6 items, 0–3).
-- Item scores stored as JSONB { item_code: 0..3 }; the catalog lives in code.
-- total_score/percentage/category are computed in the service before insert.
-- =============================================================================

CREATE TABLE parent_involvement_records (
    involvement_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baby_id                 UUID NOT NULL REFERENCES babies(baby_id),
    recorded_by             UUID NOT NULL REFERENCES users(id),
    observation_time        TIMESTAMPTZ NOT NULL,
    scores                  JSONB NOT NULL DEFAULT '{}'::jsonb,   -- { item_code: 0..3 }
    catatan                 TEXT,
    -- optional contextual fields (not part of the pillar scoring)
    durasi_menyusui         SMALLINT,            -- minutes (informational)
    durasi_interaksi        SMALLINT,            -- minutes (informational)
    kondisi_bayi            VARCHAR(255),
    total_score             INTEGER NOT NULL DEFAULT 0,           -- 0..18
    percentage              NUMERIC(5, 2) NOT NULL DEFAULT 0,     -- 0..100
    category                VARCHAR(30),                          -- Sangat Baik … Sangat Kurang
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: observations
-- 8-Pillar premature-baby observation instrument (54 items, each scored 0–3).
-- Item scores are stored as JSONB { item_code: score }; the catalog lives in code.
-- =============================================================================

CREATE TABLE observations (
    observation_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baby_id             UUID NOT NULL REFERENCES babies(baby_id),
    recorded_by         UUID NOT NULL REFERENCES users(id),
    observation_time    TIMESTAMPTZ NOT NULL,
    scores              JSONB NOT NULL DEFAULT '{}'::jsonb,   -- { item_code: 0..3 }
    catatan             TEXT,
    total_score         INTEGER NOT NULL DEFAULT 0,           -- 0..126 (6 pillars × 42 items)
    percentage          NUMERIC(5, 2) NOT NULL DEFAULT 0,     -- 0..100
    category            VARCHAR(30),                          -- Sangat Baik … Sangat Kurang
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: aksi_records
-- Menu Aksi = PILAR 8 "Kolaborasi Interprofesional" (6 items, 0–3), pulled out
-- of the Monitoring Bayi instrument. Item scores stored as JSONB { item_code: 0..3 }.
-- =============================================================================

CREATE TABLE aksi_records (
    aksi_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baby_id             UUID NOT NULL REFERENCES babies(baby_id),
    recorded_by         UUID NOT NULL REFERENCES users(id),
    observation_time    TIMESTAMPTZ NOT NULL,
    scores              JSONB NOT NULL DEFAULT '{}'::jsonb,   -- { item_code: 0..3 }
    catatan             TEXT,
    total_score         INTEGER NOT NULL DEFAULT 0,           -- 0..18
    percentage          NUMERIC(5, 2) NOT NULL DEFAULT 0,     -- 0..100
    category            VARCHAR(30),                          -- Sangat Baik … Sangat Kurang
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: doctor_notes
-- Free-text "Catatan Dokter" written by a dokter during observation of the
-- incubator/baby. Shown at the end of the report + PDF. History (append-only).
-- =============================================================================

CREATE TABLE doctor_notes (
    note_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baby_id             UUID NOT NULL REFERENCES babies(baby_id) ON DELETE CASCADE,
    recorded_by         UUID NOT NULL REFERENCES users(id),      -- the dokter
    observation_time    TIMESTAMPTZ NOT NULL,
    catatan             TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: devices  (updates03 — one IoT sensor unit per incubator)
-- =============================================================================

CREATE TABLE devices (
    device_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- UNIQUE is what enforces "one device per incubator"
    -- SET NULL, not CASCADE: the physical unit outlives the incubator row, so it
    -- keeps its key and gets a diagnosable 409 instead of needing a reflash
    incubator_id     UUID UNIQUE REFERENCES incubators(incubator_id) ON DELETE SET NULL,
    -- SHA-256 of the device key; the plaintext is shown once at provisioning
    device_key_hash  VARCHAR(64) NOT NULL UNIQUE,
    label            VARCHAR(100),
    firmware_version VARCHAR(20),
    last_seen_at     TIMESTAMPTZ,                            -- drives the online/offline badge
    -- IP is provenance, never identity: DHCP reassigns it and any LAN host can
    -- claim it. last_ip says where a reading came from; allowed_ip is an optional
    -- coarse filter (single address or CIDR) for the unauthenticated legacy route.
    last_ip          VARCHAR(45),
    allowed_ip       VARCHAR(45),
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: sensor_readings  (updates03 — high-frequency IoT telemetry)
-- =============================================================================
-- Separate from monitoring_records on purpose: that table is clinical and
-- attested (recorded_by NOT NULL), this one is machine output with no human in
-- the loop. Column types mirror it exactly so vitals auto-fill is a straight copy.
-- All metrics nullable: NULL means "the sensor had nothing to report".

CREATE TABLE sensor_readings (
    reading_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incubator_id         UUID NOT NULL REFERENCES incubators(incubator_id) ON DELETE CASCADE,
    -- denormalized from the active assignment at ingest; NULL for an idle unit
    baby_id              UUID REFERENCES babies(baby_id) ON DELETE SET NULL,
    device_id            UUID REFERENCES devices(device_id) ON DELETE SET NULL,
    -- server-assigned: the ESP8266 has no RTC and runs no NTP
    recorded_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    suhu_bayi            NUMERIC(4,1),                       -- °C, DS18B20
    suhu_inkubator       NUMERIC(4,1),                       -- °C, DHT22
    kelembapan_inkubator NUMERIC(5,2),                       -- % RH, DHT22
    heart_rate           SMALLINT,                           -- bpm, MAX30102
    spo2                 NUMERIC(5,2),                       -- %, MAX30102
    respiratory_rate     SMALLINT,                           -- no sensor yet; parity column
    source               sensor_source NOT NULL DEFAULT 'sensor',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: audit_logs
-- Immutable trail of all user actions
-- =============================================================================

CREATE TABLE audit_logs (
    log_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    action          VARCHAR(50) NOT NULL,   -- LOGIN, CREATE, UPDATE, DELETE, EXPORT
    table_name      VARCHAR(100),
    record_id       UUID,
    ip_address      INET,
    details         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- monitoring_records — most queried by baby + time
CREATE INDEX idx_monitoring_baby_time    ON monitoring_records (baby_id, observation_time DESC);
CREATE INDEX idx_monitoring_recorded_by  ON monitoring_records (recorded_by);

-- parent_involvement — queried by baby
CREATE INDEX idx_involvement_baby_time   ON parent_involvement_records (baby_id, observation_time DESC);

-- observations — queried by baby + time
CREATE INDEX idx_observation_baby_time   ON observations (baby_id, observation_time DESC);

-- aksi_records — queried by baby + time
CREATE INDEX idx_aksi_baby_time          ON aksi_records (baby_id, observation_time DESC);

-- doctor_notes — queried by baby + time
CREATE INDEX ix_doctor_notes_baby        ON doctor_notes (baby_id, observation_time DESC);

-- assignments — find active assignment for a baby or incubator quickly
CREATE INDEX idx_assignment_baby         ON baby_incubator_assignments (baby_id);
CREATE INDEX idx_assignment_incubator    ON baby_incubator_assignments (incubator_id);

-- sensor_readings — the chart backfill: newest N for one incubator
CREATE INDEX idx_sensor_readings_incubator_time ON sensor_readings (incubator_id, recorded_at DESC);

-- =============================================================================
-- TABLE: sensor_reading_minutes  (updates03 P4 — 1-minute rollups)
-- =============================================================================
-- Raw readings are dropped after the retention window; these keep the shape of
-- the history at ~1/20th the rows. avg AND min/max, because a one-minute mean
-- would smooth away a ten-second desaturation — the event worth keeping.
CREATE TABLE sensor_reading_minutes (
    bucket_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incubator_id   UUID NOT NULL REFERENCES incubators(incubator_id) ON DELETE CASCADE,
    baby_id        UUID REFERENCES babies(baby_id) ON DELETE SET NULL,
    minute         TIMESTAMPTZ NOT NULL,
    -- how many raw samples this row stands for; 4 samples is weaker evidence than 20
    sample_count   SMALLINT NOT NULL,
    suhu_bayi_avg              NUMERIC(4,1),
    suhu_bayi_min              NUMERIC(4,1),
    suhu_bayi_max              NUMERIC(4,1),
    suhu_inkubator_avg         NUMERIC(4,1),
    suhu_inkubator_min         NUMERIC(4,1),
    suhu_inkubator_max         NUMERIC(4,1),
    kelembapan_inkubator_avg   NUMERIC(5,2),
    kelembapan_inkubator_min   NUMERIC(5,2),
    kelembapan_inkubator_max   NUMERIC(5,2),
    heart_rate_avg             NUMERIC(5,1),
    heart_rate_min             NUMERIC(5,1),
    heart_rate_max             NUMERIC(5,1),
    spo2_avg                   NUMERIC(5,2),
    spo2_min                   NUMERIC(5,2),
    spo2_max                   NUMERIC(5,2),
    -- makes the rollup idempotent: re-running a window updates instead of duplicating
    CONSTRAINT uq_sensor_minutes_incubator_minute UNIQUE (incubator_id, minute)
);

CREATE INDEX idx_sensor_minutes_incubator_time
    ON sensor_reading_minutes (incubator_id, minute DESC);

-- =============================================================================
-- TABLE: sensor_alerts  (updates03 P4 — threshold breaches raised at ingest)
-- =============================================================================
CREATE TABLE sensor_alerts (
    alert_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incubator_id    UUID NOT NULL REFERENCES incubators(incubator_id) ON DELETE CASCADE,
    -- which baby was in the incubator when this fired; nullable because an empty
    -- incubator can still alert on air temperature
    baby_id         UUID REFERENCES babies(baby_id) ON DELETE SET NULL,
    alert_type      sensor_alert_type NOT NULL,
    metric_key      VARCHAR(40) NOT NULL,
    severity        sensor_alert_severity NOT NULL DEFAULT 'warning',
    -- the reading that opened it and the bound it crossed, so the alert stays
    -- readable even after an admin edits the thresholds
    value           NUMERIC(6,2),
    threshold       NUMERIC(6,2),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    acknowledged_by UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- the alert feed for one incubator, newest first
CREATE INDEX idx_sensor_alerts_incubator_time
    ON sensor_alerts (incubator_id, started_at DESC);

-- At most ONE open alert per incubator per type. This is what makes the engine
-- idempotent: a breach lasting a minute refreshes one row rather than opening 20.
CREATE UNIQUE INDEX idx_sensor_alerts_open_unique
    ON sensor_alerts (incubator_id, alert_type) WHERE resolved_at IS NULL;

-- audit_logs — queried by user and time
CREATE INDEX idx_audit_user_time         ON audit_logs (user_id, created_at DESC);
CREATE INDEX idx_audit_table_record      ON audit_logs (table_name, record_id);

-- =============================================================================
-- updated_at auto-update trigger
-- =============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_incubators_updated_at
    BEFORE UPDATE ON incubators
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_babies_updated_at
    BEFORE UPDATE ON babies
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_parents_updated_at
    BEFORE UPDATE ON parents
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_devices_updated_at
    BEFORE UPDATE ON devices
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
