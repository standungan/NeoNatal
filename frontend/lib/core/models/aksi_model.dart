// Menu Aksi — PILAR 8: KOLABORASI INTERPROFESIONAL.
// 6 items, each scored 0–3 (mirrors the backend aksi_catalog).
// Shared scoring helpers live in core/models/scoring.dart.

/// [item_code, text] for the 6 Kolaborasi Interprofesional items.
const kAksiItems = <List<String>>[
  ['kolaborasi_1', 'Catatan CPPT lengkap'],
  ['kolaborasi_2', 'SBAR dilakukan saat handover'],
  ['kolaborasi_3', 'Instruksi dokter terdokumentasi'],
  ['kolaborasi_4', 'Perubahan kondisi bayi segera dilaporkan'],
  ['kolaborasi_5', 'Kolaborasi dokter-perawat berjalan baik'],
  ['kolaborasi_6', 'Seluruh tindakan terdokumentasi'],
];

const kAksiMaxTotal = 18; // 6 items × 3
