// Keterlibatan Orang Tua — PILAR 6: KERJASAMA DENGAN KELUARGA.
// 6 items, each scored 0–3 (mirrors the backend involvement_catalog).
// Shared scoring helpers live in core/models/scoring.dart.

/// [item_code, text] for the 6 Pillar-6 items.
const kInvolvementItems = <List<String>>[
  ['keluarga_1', 'Ibu memberikan ASI/perah ASI'],
  ['keluarga_2', 'Keluarga memahami kondisi bayi'],
  ['keluarga_3', 'Keluarga terlibat dalam PMK'],
  ['keluarga_4', 'Keluarga membantu perawatan dasar'],
  ['keluarga_5', 'Keluarga mengikuti edukasi'],
  ['keluarga_6', 'Keluarga memahami perawatan di rumah'],
];

const kInvolvementMaxTotal = 18; // 6 items × 3
