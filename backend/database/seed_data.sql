-- =============================================================================
-- Seed Data — Sistem Monitoring Bayi pada Inkubator
-- Run AFTER schema.sql
-- Passwords below are bcrypt hashes of "Password123!"
-- =============================================================================

-- =============================================================================
-- USERS
-- =============================================================================

INSERT INTO users (id, role, email, password_hash, full_name) VALUES
(
    'aaaaaaaa-0001-0001-0001-000000000001',
    'admin',
    'admin@neonatal.rs',
    '$2b$12$mVNFQ/MY10L6vCb8hx9C9eXKfnWQGZHQDkBu3a.oZYhgQR5Xtjn0K',
    'Administrator Sistem'
),
(
    'aaaaaaaa-0001-0001-0001-000000000002',
    'perawat',
    'siti.aisyah@neonatal.rs',
    '$2b$12$mVNFQ/MY10L6vCb8hx9C9eXKfnWQGZHQDkBu3a.oZYhgQR5Xtjn0K',
    'Siti Aisyah'
),
(
    'aaaaaaaa-0001-0001-0001-000000000003',
    'perawat',
    'budi.santoso@neonatal.rs',
    '$2b$12$mVNFQ/MY10L6vCb8hx9C9eXKfnWQGZHQDkBu3a.oZYhgQR5Xtjn0K',
    'Budi Santoso'
),
(
    'aaaaaaaa-0001-0001-0001-000000000004',
    'dokter',
    'dr.anisa@neonatal.rs',
    '$2b$12$mVNFQ/MY10L6vCb8hx9C9eXKfnWQGZHQDkBu3a.oZYhgQR5Xtjn0K',
    'dr. Anisa Permata, Sp.A'
);

-- =============================================================================
-- INCUBATORS
-- =============================================================================

INSERT INTO incubators (incubator_id, incubator_no, location, status) VALUES
('bbbbbbbb-0002-0002-0002-000000000001', '01', 'NICU Ruang A', 'terisi'),
('bbbbbbbb-0002-0002-0002-000000000002', '02', 'NICU Ruang A', 'terisi'),
('bbbbbbbb-0002-0002-0002-000000000003', '03', 'NICU Ruang A', 'kosong'),
('bbbbbbbb-0002-0002-0002-000000000004', '04', 'NICU Ruang A', 'warning'),
('bbbbbbbb-0002-0002-0002-000000000005', '05', 'NICU Ruang B', 'terisi'),
('bbbbbbbb-0002-0002-0002-000000000006', '06', 'NICU Ruang B', 'kosong');

-- =============================================================================
-- BABIES
-- =============================================================================

INSERT INTO babies (baby_id, baby_name, gender, birth_date, birth_weight, birth_length, gestational_age, birth_type) VALUES
(
    'cccccccc-0003-0003-0003-000000000001',
    'Ahmad Rizki',
    'laki_laki',
    '2025-05-12',
    2400.00, 46.0, 35, 'SC'
),
(
    'cccccccc-0003-0003-0003-000000000002',
    'Siti Aisyah',
    'perempuan',
    '2025-05-13',
    1950.00, 42.5, 33, 'Normal'
),
(
    'cccccccc-0003-0003-0003-000000000003',
    'Muhammad Farhan',
    'laki_laki',
    '2025-05-10',
    2100.00, 44.0, 34, 'Normal'
),
(
    'cccccccc-0003-0003-0003-000000000004',
    'Hana Putri',
    'perempuan',
    '2025-05-15',
    2800.00, 48.0, 37, 'SC'
);

-- =============================================================================
-- PARENTS
-- =============================================================================

INSERT INTO parents (baby_id, mother_name, father_name, mother_phone, mother_medical_history) VALUES
('cccccccc-0003-0003-0003-000000000001', 'Rina Dewi',    'Budi Rizki',  '081234567890', 'Hipertensi ringan'),
('cccccccc-0003-0003-0003-000000000002', 'Kartini',      'Hasan',       '082345678901', NULL),
('cccccccc-0003-0003-0003-000000000003', 'Yuni Astuti',  'Farhan Sr',   '083456789012', 'Diabetes gestasional'),
('cccccccc-0003-0003-0003-000000000004', 'Dewi Lestari', 'Anton',       '084567890123', NULL);

-- =============================================================================
-- BABY_INCUBATOR_ASSIGNMENTS
-- =============================================================================

INSERT INTO baby_incubator_assignments (baby_id, incubator_id, assigned_by, assigned_at, status) VALUES
(
    'cccccccc-0003-0003-0003-000000000001',
    'bbbbbbbb-0002-0002-0002-000000000001',
    'aaaaaaaa-0001-0001-0001-000000000002',
    '2025-05-12 08:00:00+07',
    'active'
),
(
    'cccccccc-0003-0003-0003-000000000002',
    'bbbbbbbb-0002-0002-0002-000000000002',
    'aaaaaaaa-0001-0001-0001-000000000002',
    '2025-05-13 09:30:00+07',
    'active'
),
(
    'cccccccc-0003-0003-0003-000000000003',
    'bbbbbbbb-0002-0002-0002-000000000004',
    'aaaaaaaa-0001-0001-0001-000000000003',
    '2025-05-10 07:15:00+07',
    'active'
),
(
    'cccccccc-0003-0003-0003-000000000004',
    'bbbbbbbb-0002-0002-0002-000000000005',
    'aaaaaaaa-0001-0001-0001-000000000002',
    '2025-05-15 10:00:00+07',
    'active'
);

-- =============================================================================
-- MONITORING_RECORDS (a few samples per baby)
-- =============================================================================

INSERT INTO monitoring_records
    (baby_id, recorded_by, observation_time, suhu_bayi, suhu_inkubator, heart_rate, spo2, expression_score, movement_score)
VALUES
-- Ahmad Rizki — Inkubator 01
(
    'cccccccc-0003-0003-0003-000000000001',
    'aaaaaaaa-0001-0001-0001-000000000002',
    '2025-05-16 09:30:00+07',
    36.8, 33.5, 128, 98.00, 3, 4
),
(
    'cccccccc-0003-0003-0003-000000000001',
    'aaaaaaaa-0001-0001-0001-000000000002',
    '2025-05-16 14:00:00+07',
    37.0, 33.8, 132, 97.50, 4, 4
),
-- Siti Aisyah — Inkubator 02
(
    'cccccccc-0003-0003-0003-000000000002',
    'aaaaaaaa-0001-0001-0001-000000000002',
    '2025-05-16 10:00:00+07',
    37.1, 34.0, 135, 96.00, 2, 3
),
-- Muhammad Farhan — Inkubator 04 (warning)
(
    'cccccccc-0003-0003-0003-000000000003',
    'aaaaaaaa-0001-0001-0001-000000000003',
    '2025-05-16 09:00:00+07',
    37.6, 34.5, 160, 92.00, 2, 2
);

-- =============================================================================
-- PARENT_INVOLVEMENT_RECORDS
-- =============================================================================

INSERT INTO parent_involvement_records
    (baby_id, recorded_by, observation_time, durasi_menyusui, durasi_interaksi, skor_keterlibatan, kondisi_bayi)
VALUES
(
    'cccccccc-0003-0003-0003-000000000001',
    'aaaaaaaa-0001-0001-0001-000000000002',
    '2025-05-16 11:00:00+07',
    20, 45, 78, 'Tenang'
),
(
    'cccccccc-0003-0003-0003-000000000002',
    'aaaaaaaa-0001-0001-0001-000000000002',
    '2025-05-16 11:30:00+07',
    10, 30, 52, 'Aktif'
);
