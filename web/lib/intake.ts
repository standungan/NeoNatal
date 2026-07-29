// Option lists for the baby-registration / NICU-intake form (updates02).
// Enum values mirror the backend; checklist strings are stored verbatim in JSONB,
// so they must stay consistent with the seed/backend.

export const BLOOD_TYPES = ["A", "B", "AB", "O"] as const;

export const PENDIDIKAN: { value: string; label: string }[] = [
  { value: "tidak_sekolah", label: "Tidak Sekolah" },
  { value: "sd", label: "SD" },
  { value: "smp", label: "SMP" },
  { value: "sma", label: "SMA" },
  { value: "diploma", label: "Diploma" },
  { value: "s1", label: "S1" },
  { value: "s2", label: "S2" },
  { value: "s3", label: "S3" },
];

export const JENIS_PERSALINAN: { value: string; label: string }[] = [
  { value: "normal", label: "Normal" },
  { value: "sc", label: "Sectio Caesarea (SC)" },
  { value: "vakum", label: "Vakum" },
  { value: "forceps", label: "Forceps" },
];

export const KONDISI_UMUM: { value: string; label: string }[] = [
  { value: "baik", label: "Baik" },
  { value: "cukup", label: "Cukup" },
  { value: "buruk", label: "Buruk" },
];

export const JENIS_KEHAMILAN: { value: string; label: string }[] = [
  { value: "tunggal", label: "Tunggal" },
  { value: "kembar", label: "Kembar" },
];

// D.4 — indikasi persalinan prematur (checklist)
export const INDIKASI_PREMATUR: string[] = [
  "Persalinan prematur spontan",
  "Ketuban pecah dini (PPROM)",
  "Preeklamsia",
  "Eklampsia",
  "Hipertensi ibu",
  "Diabetes gestasional",
  "Perdarahan plasenta previa",
  "Solusio plasenta",
  "Pertumbuhan janin terhambat (IUGR)",
  "Gawat janin",
  "Kehamilan kembar",
  "Infeksi ibu",
  "Kelainan bawaan janin",
];

// D.5 — komplikasi persalinan (checklist)
export const KOMPLIKASI_PERSALINAN: string[] = [
  "Tidak ada komplikasi",
  "Perdarahan",
  "Ketuban pecah dini (KPD/PPROM)",
  "Persalinan lama",
  "Gawat janin",
  "Preeklamsia",
  "Eklampsia",
  "Solusio plasenta",
  "Plasenta previa",
  "Infeksi (Korioamnionitis)",
  "Prolaps tali pusat",
  "Lilitan tali pusat",
  "Distosia bahu",
  "Aspirasi mekonium",
  "Ruptur uteri",
  "Retensio plasenta",
  "Atonia uteri",
  "Syok",
];
