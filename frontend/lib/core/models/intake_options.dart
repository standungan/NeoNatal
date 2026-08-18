// Option lists for the baby-registration / NICU-intake form (updates02).
// Mirrors web/lib/intake.ts and the backend enums. Checklist strings are stored
// verbatim in JSONB, so they must stay consistent with the seed/backend.

const kBloodTypes = <String>['A', 'B', 'AB', 'O'];

// (value, label)
const kPendidikan = <(String, String)>[
  ('tidak_sekolah', 'Tidak Sekolah'),
  ('sd', 'SD'),
  ('smp', 'SMP'),
  ('sma', 'SMA'),
  ('diploma', 'Diploma'),
  ('s1', 'S1'),
  ('s2', 'S2'),
  ('s3', 'S3'),
];

const kJenisPersalinan = <(String, String)>[
  ('normal', 'Normal'),
  ('sc', 'Sectio Caesarea (SC)'),
  ('vakum', 'Vakum'),
  ('forceps', 'Forceps'),
];

const kKondisiUmum = <(String, String)>[
  ('baik', 'Baik'),
  ('cukup', 'Cukup'),
  ('buruk', 'Buruk'),
];

const kJenisKehamilan = <(String, String)>[
  ('tunggal', 'Tunggal'),
  ('kembar', 'Kembar'),
];

// D.4 — indikasi persalinan prematur (checklist)
const kIndikasiPrematur = <String>[
  'Persalinan prematur spontan',
  'Ketuban pecah dini (PPROM)',
  'Preeklamsia',
  'Eklampsia',
  'Hipertensi ibu',
  'Diabetes gestasional',
  'Perdarahan plasenta previa',
  'Solusio plasenta',
  'Pertumbuhan janin terhambat (IUGR)',
  'Gawat janin',
  'Kehamilan kembar',
  'Infeksi ibu',
  'Kelainan bawaan janin',
];

// D.5 — komplikasi persalinan (checklist)
const kKomplikasiPersalinan = <String>[
  'Tidak ada komplikasi',
  'Perdarahan',
  'Ketuban pecah dini (KPD/PPROM)',
  'Persalinan lama',
  'Gawat janin',
  'Preeklamsia',
  'Eklampsia',
  'Solusio plasenta',
  'Plasenta previa',
  'Infeksi (Korioamnionitis)',
  'Prolaps tali pusat',
  'Lilitan tali pusat',
  'Distosia bahu',
  'Aspirasi mekonium',
  'Ruptur uteri',
  'Retensio plasenta',
  'Atonia uteri',
  'Syok',
];
