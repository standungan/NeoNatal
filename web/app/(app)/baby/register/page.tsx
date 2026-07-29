"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, SectionTitle, BackLink } from "@/components/ui";
import {
  Field,
  TextInput,
  NumberInput,
  TextArea,
  Select,
  YesNo,
  CheckboxGroup,
  SubmitButton,
  Banner,
  errorMessage,
} from "@/components/form";
import {
  BLOOD_TYPES,
  PENDIDIKAN,
  JENIS_PERSALINAN,
  KONDISI_UMUM,
  JENIS_KEHAMILAN,
  INDIKASI_PREMATUR,
  KOMPLIKASI_PERSALINAN,
} from "@/lib/intake";
import type { BabyDetail } from "@/lib/types";

interface AvailableIncubator {
  incubator_id: string;
  incubator_no: string;
  location: string | null;
}
interface DoctorOption {
  id: string;
  full_name: string;
}

type MatState = {
  no_rm_ibu: string; umur_ibu: string; pendidikan: string; pekerjaan: string; alamat: string; golongan_darah: string;
  kehamilan_ke: string; jumlah_persalinan_hidup: string;
  riwayat_abortus: boolean | null; riwayat_prematur: boolean | null; riwayat_bblr: boolean | null; riwayat_bayi_meninggal: boolean | null;
  usia_kehamilan_lahir: string; jenis_kehamilan: string; anc_rutin: boolean | null; jumlah_anc: string;
  hipertensi_kehamilan: boolean | null; preeklamsia: boolean | null; diabetes_gestasional: boolean | null;
  infeksi_hamil: boolean | null; perdarahan_hamil: boolean | null; ketuban_pecah_dini: boolean | null;
  merokok: boolean | null; paparan_asap_rokok: boolean | null; konsumsi_alkohol: boolean | null;
  obat_tertentu: boolean | null; obat_tertentu_ket: string;
  tanggal_persalinan: string; jenis_persalinan: string; tempat_persalinan: string;
  indikasi_prematur: string[]; indikasi_prematur_lainnya: string;
  komplikasi_persalinan: string[]; komplikasi_lainnya: string;
  apgar_menit_1: string; apgar_menit_5: string;
  kondisi_umum: string; masih_dirawat: boolean | null; komplikasi_postpartum: boolean | null;
  dapat_berjalan: boolean | null; dapat_menyusui: boolean | null;
};

type BoolKeys = { [K in keyof MatState]: MatState[K] extends boolean | null ? K : never }[keyof MatState];
type StrKeys = { [K in keyof MatState]: MatState[K] extends string ? K : never }[keyof MatState];

const EMPTY_MAT: MatState = {
  no_rm_ibu: "", umur_ibu: "", pendidikan: "", pekerjaan: "", alamat: "", golongan_darah: "",
  kehamilan_ke: "", jumlah_persalinan_hidup: "",
  riwayat_abortus: null, riwayat_prematur: null, riwayat_bblr: null, riwayat_bayi_meninggal: null,
  usia_kehamilan_lahir: "", jenis_kehamilan: "", anc_rutin: null, jumlah_anc: "",
  hipertensi_kehamilan: null, preeklamsia: null, diabetes_gestasional: null,
  infeksi_hamil: null, perdarahan_hamil: null, ketuban_pecah_dini: null,
  merokok: null, paparan_asap_rokok: null, konsumsi_alkohol: null,
  obat_tertentu: null, obat_tertentu_ket: "",
  tanggal_persalinan: "", jenis_persalinan: "", tempat_persalinan: "",
  indikasi_prematur: [], indikasi_prematur_lainnya: "",
  komplikasi_persalinan: [], komplikasi_lainnya: "",
  apgar_menit_1: "", apgar_menit_5: "",
  kondisi_umum: "", masih_dirawat: null, komplikasi_postpartum: null,
  dapat_berjalan: null, dapat_menyusui: null,
};

const num = (s: string) => (s.trim() === "" ? null : Number(s));

export default function RegisterBabyPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const { data: incubators } = useQuery({
    queryKey: ["incubators", "available"],
    queryFn: async () => (await api.get<AvailableIncubator[]>("/incubators/available")).data,
  });
  const { data: doctors } = useQuery({
    queryKey: ["users", "doctors"],
    queryFn: async () => (await api.get<DoctorOption[]>("/users/doctors")).data,
  });

  const [f, setF] = useState({
    // baby identity
    baby_name: "", gender: "laki_laki", birth_date: "", birth_weight: "", birth_length: "",
    gestational_age: "", birth_type: "", clinical_notes: "",
    no_rm_bayi: "", jam_lahir: "", usia_masuk_nicu_jam: "", lingkar_kepala: "", lingkar_dada: "", golongan_darah: "",
    // parent
    mother_name: "", father_name: "", mother_phone: "",
    // registration
    incubator_id: "", rumah_sakit: "", ruang_nicu: "", dpjp_id: "",
  });
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) =>
    setF((s) => ({ ...s, [k]: e.target.value }));

  const [mat, setMat] = useState<MatState>(EMPTY_MAT);
  const [showMat, setShowMat] = useState(true);

  // typed maternal-field helpers
  const yn = (label: string, k: BoolKeys) => (
    <Field label={label}>
      <YesNo value={mat[k]} onChange={(v) => setMat((s) => ({ ...s, [k]: v }))} />
    </Field>
  );
  const mstr = (label: string, k: StrKeys, placeholder?: string, type?: string) => (
    <Field label={label}>
      <TextInput type={type} value={mat[k]} placeholder={placeholder}
        onChange={(e) => setMat((s) => ({ ...s, [k]: e.target.value }))} />
    </Field>
  );
  const mnum = (label: string, k: StrKeys, placeholder?: string) => (
    <Field label={label}>
      <NumberInput value={mat[k]} placeholder={placeholder}
        onChange={(e) => setMat((s) => ({ ...s, [k]: e.target.value }))} />
    </Field>
  );

  const maternalFilled = () =>
    Object.values(mat).some((v) =>
      Array.isArray(v) ? v.length > 0 : typeof v === "boolean" ? true : String(v).trim() !== "",
    );

  const buildMaternal = () => ({
    no_rm_ibu: mat.no_rm_ibu.trim() || null,
    umur_ibu: num(mat.umur_ibu),
    pendidikan: mat.pendidikan || null,
    pekerjaan: mat.pekerjaan.trim() || null,
    alamat: mat.alamat.trim() || null,
    golongan_darah: mat.golongan_darah || null,
    kehamilan_ke: num(mat.kehamilan_ke),
    jumlah_persalinan_hidup: num(mat.jumlah_persalinan_hidup),
    riwayat_abortus: mat.riwayat_abortus,
    riwayat_prematur: mat.riwayat_prematur,
    riwayat_bblr: mat.riwayat_bblr,
    riwayat_bayi_meninggal: mat.riwayat_bayi_meninggal,
    usia_kehamilan_lahir: num(mat.usia_kehamilan_lahir),
    jenis_kehamilan: mat.jenis_kehamilan || null,
    anc_rutin: mat.anc_rutin,
    jumlah_anc: num(mat.jumlah_anc),
    hipertensi_kehamilan: mat.hipertensi_kehamilan,
    preeklamsia: mat.preeklamsia,
    diabetes_gestasional: mat.diabetes_gestasional,
    infeksi_hamil: mat.infeksi_hamil,
    perdarahan_hamil: mat.perdarahan_hamil,
    ketuban_pecah_dini: mat.ketuban_pecah_dini,
    merokok: mat.merokok,
    paparan_asap_rokok: mat.paparan_asap_rokok,
    konsumsi_alkohol: mat.konsumsi_alkohol,
    obat_tertentu: mat.obat_tertentu,
    obat_tertentu_ket: mat.obat_tertentu_ket.trim() || null,
    tanggal_persalinan: mat.tanggal_persalinan || null,
    jenis_persalinan: mat.jenis_persalinan || null,
    tempat_persalinan: mat.tempat_persalinan.trim() || null,
    indikasi_prematur: mat.indikasi_prematur.length ? mat.indikasi_prematur : null,
    indikasi_prematur_lainnya: mat.indikasi_prematur_lainnya.trim() || null,
    komplikasi_persalinan: mat.komplikasi_persalinan.length ? mat.komplikasi_persalinan : null,
    komplikasi_lainnya: mat.komplikasi_lainnya.trim() || null,
    apgar_menit_1: num(mat.apgar_menit_1),
    apgar_menit_5: num(mat.apgar_menit_5),
    kondisi_umum: mat.kondisi_umum || null,
    masih_dirawat: mat.masih_dirawat,
    komplikasi_postpartum: mat.komplikasi_postpartum,
    dapat_berjalan: mat.dapat_berjalan,
    dapat_menyusui: mat.dapat_menyusui,
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const body = {
        baby_name: f.baby_name.trim(),
        gender: f.gender,
        birth_date: f.birth_date,
        birth_weight: num(f.birth_weight),
        birth_length: num(f.birth_length),
        gestational_age: num(f.gestational_age),
        birth_type: f.birth_type.trim() || null,
        clinical_notes: f.clinical_notes.trim() || null,
        no_rm_bayi: f.no_rm_bayi.trim() || null,
        jam_lahir: f.jam_lahir || null,
        usia_masuk_nicu_jam: num(f.usia_masuk_nicu_jam),
        lingkar_kepala: num(f.lingkar_kepala),
        lingkar_dada: num(f.lingkar_dada),
        golongan_darah: f.golongan_darah || null,
        parent: {
          mother_name: f.mother_name.trim() || null,
          father_name: f.father_name.trim() || null,
          mother_phone: f.mother_phone.trim() || null,
        },
        maternal: maternalFilled() ? buildMaternal() : null,
        incubator_id: f.incubator_id,
        rumah_sakit: f.rumah_sakit.trim() || null,
        ruang_nicu: f.ruang_nicu.trim() || null,
        dpjp_id: f.dpjp_id || null,
      };
      return (await api.post<BabyDetail>("/babies", body)).data;
    },
    onSuccess: (baby) => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["incubators", "available"] });
      router.push(`/baby/${baby.baby_id}/report`);
    },
  });

  const valid = f.baby_name.trim() && f.birth_date && f.incubator_id;

  return (
    <div>
      <BackLink href="/dashboard" label="Kembali ke Dashboard" />
      <h1 className="mb-4 mt-3 text-xl font-extrabold text-ink">Registrasi Bayi Baru</h1>

      <form onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }} className="flex flex-col gap-4">
        {/* ── Identitas Bayi ── */}
        <Card className="flex flex-col gap-4 p-5">
          <SectionTitle>Identitas Bayi</SectionTitle>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Nama Bayi"><TextInput value={f.baby_name} onChange={set("baby_name")} placeholder="Nama bayi" required /></Field>
            <Field label="No. Rekam Medis Bayi"><TextInput value={f.no_rm_bayi} onChange={set("no_rm_bayi")} placeholder="RM-…" /></Field>
            <Field label="Jenis Kelamin">
              <Select value={f.gender} onChange={set("gender")}>
                <option value="laki_laki">Laki-laki</option>
                <option value="perempuan">Perempuan</option>
              </Select>
            </Field>
            <Field label="Golongan Darah">
              <Select value={f.golongan_darah} onChange={set("golongan_darah")}>
                <option value="">—</option>
                {BLOOD_TYPES.map((b) => <option key={b} value={b}>{b}</option>)}
              </Select>
            </Field>
            <Field label="Tanggal Lahir"><input type="date" className="input" value={f.birth_date} onChange={set("birth_date")} required /></Field>
            <Field label="Jam Lahir"><input type="time" className="input" value={f.jam_lahir} onChange={set("jam_lahir")} /></Field>
            <Field label="Usia Gestasi (minggu)"><NumberInput value={f.gestational_age} onChange={set("gestational_age")} placeholder="36" /></Field>
            <Field label="Usia Masuk NICU (jam)"><NumberInput value={f.usia_masuk_nicu_jam} onChange={set("usia_masuk_nicu_jam")} placeholder="6" /></Field>
            <Field label="Berat Lahir (gram)"><NumberInput value={f.birth_weight} onChange={set("birth_weight")} placeholder="2400" /></Field>
            <Field label="Panjang Lahir (cm)"><NumberInput value={f.birth_length} onChange={set("birth_length")} placeholder="47" /></Field>
            <Field label="Lingkar Kepala (cm)"><NumberInput value={f.lingkar_kepala} onChange={set("lingkar_kepala")} placeholder="29.5" /></Field>
            <Field label="Lingkar Dada (cm)"><NumberInput value={f.lingkar_dada} onChange={set("lingkar_dada")} placeholder="27.0" /></Field>
            <Field label="Jenis Kelahiran"><TextInput value={f.birth_type} onChange={set("birth_type")} placeholder="Normal / Caesar" /></Field>
          </div>
          <Field label="Catatan Klinis (opsional)"><TextArea rows={2} value={f.clinical_notes} onChange={set("clinical_notes")} /></Field>
        </Card>

        {/* ── Data Registrasi ── */}
        <Card className="flex flex-col gap-4 p-5">
          <SectionTitle>Data Registrasi</SectionTitle>
          <p className="-mt-2 text-[12px] text-muted">No. Registrasi NICU dibuat otomatis oleh sistem saat disimpan.</p>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Rumah Sakit"><TextInput value={f.rumah_sakit} onChange={set("rumah_sakit")} placeholder="Nama rumah sakit" /></Field>
            <Field label="Ruang NICU"><TextInput value={f.ruang_nicu} onChange={set("ruang_nicu")} placeholder="NICU Ruang A" /></Field>
            <Field label="Dokter Penanggung Jawab (DPJP)">
              <Select value={f.dpjp_id} onChange={set("dpjp_id")}>
                <option value="">— Pilih dokter —</option>
                {(doctors ?? []).map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
              </Select>
            </Field>
            <Field label="Inkubator (kosong)">
              <Select value={f.incubator_id} onChange={set("incubator_id")} required>
                <option value="">— Pilih inkubator —</option>
                {(incubators ?? []).map((inc) => (
                  <option key={inc.incubator_id} value={inc.incubator_id}>
                    No. {inc.incubator_no}{inc.location ? ` — ${inc.location}` : ""}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          {incubators && incubators.length === 0 && (
            <p className="text-[12px] text-warn">Tidak ada inkubator kosong tersedia.</p>
          )}
        </Card>

        {/* ── Data Orang Tua ── */}
        <Card className="flex flex-col gap-4 p-5">
          <SectionTitle>Data Orang Tua</SectionTitle>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Nama Ibu"><TextInput value={f.mother_name} onChange={set("mother_name")} /></Field>
            <Field label="Nama Ayah"><TextInput value={f.father_name} onChange={set("father_name")} /></Field>
            <Field label="No. Telepon Ibu"><TextInput value={f.mother_phone} onChange={set("mother_phone")} /></Field>
          </div>
        </Card>

        {/* ── Rekam Medis Ibu (collapsible) ── */}
        <Card className="flex flex-col gap-4 p-5">
          <div className="flex items-center justify-between">
            <SectionTitle>Rekam Medis Ibu (opsional)</SectionTitle>
            <button type="button" onClick={() => setShowMat((v) => !v)}
              className="rounded-lg border border-line px-3 py-1.5 text-xs font-semibold text-muted hover:bg-surface">
              {showMat ? "Sembunyikan" : "Tampilkan"}
            </button>
          </div>

          {showMat && (
            <div className="flex flex-col gap-5">
              {/* A. Identitas Ibu */}
              <div className="flex flex-col gap-3">
                <p className="text-[13px] font-bold text-ink">A. Identitas Ibu</p>
                <div className="grid grid-cols-2 gap-3">
                  {mstr("No. Rekam Medis Ibu", "no_rm_ibu")}
                  {mnum("Umur Ibu (tahun)", "umur_ibu", "29")}
                  <Field label="Pendidikan Terakhir">
                    <Select value={mat.pendidikan} onChange={(e) => setMat((s) => ({ ...s, pendidikan: e.target.value }))}>
                      <option value="">—</option>
                      {PENDIDIKAN.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
                    </Select>
                  </Field>
                  {mstr("Pekerjaan", "pekerjaan")}
                  <Field label="Golongan Darah">
                    <Select value={mat.golongan_darah} onChange={(e) => setMat((s) => ({ ...s, golongan_darah: e.target.value }))}>
                      <option value="">—</option>
                      {BLOOD_TYPES.map((b) => <option key={b} value={b}>{b}</option>)}
                    </Select>
                  </Field>
                </div>
                {mstr("Alamat", "alamat")}
              </div>

              {/* B. Riwayat Obstetri */}
              <div className="flex flex-col gap-3 border-t border-line pt-4">
                <p className="text-[13px] font-bold text-ink">B. Riwayat Obstetri</p>
                <div className="grid grid-cols-2 gap-3">
                  {mnum("Kehamilan ke-", "kehamilan_ke", "2")}
                  {mnum("Jumlah Persalinan Hidup", "jumlah_persalinan_hidup", "1")}
                  {yn("Riwayat abortus", "riwayat_abortus")}
                  {yn("Riwayat persalinan prematur sebelumnya", "riwayat_prematur")}
                  {yn("Riwayat bayi BBLR sebelumnya", "riwayat_bblr")}
                  {yn("Riwayat bayi meninggal", "riwayat_bayi_meninggal")}
                </div>
              </div>

              {/* C. Riwayat Kehamilan Saat Ini */}
              <div className="flex flex-col gap-3 border-t border-line pt-4">
                <p className="text-[13px] font-bold text-ink">C. Riwayat Kehamilan Saat Ini</p>
                <div className="grid grid-cols-2 gap-3">
                  {mnum("Usia kehamilan saat melahirkan (minggu)", "usia_kehamilan_lahir", "33")}
                  <Field label="Kehamilan tunggal / kembar">
                    <Select value={mat.jenis_kehamilan} onChange={(e) => setMat((s) => ({ ...s, jenis_kehamilan: e.target.value }))}>
                      <option value="">—</option>
                      {JENIS_KEHAMILAN.map((j) => <option key={j.value} value={j.value}>{j.label}</option>)}
                    </Select>
                  </Field>
                  {yn("Rutin ANC", "anc_rutin")}
                  {mnum("Jumlah kunjungan ANC", "jumlah_anc", "6")}
                  {yn("Hipertensi kehamilan", "hipertensi_kehamilan")}
                  {yn("Preeklamsia", "preeklamsia")}
                  {yn("Diabetes gestasional", "diabetes_gestasional")}
                  {yn("Infeksi selama hamil", "infeksi_hamil")}
                  {yn("Perdarahan selama kehamilan", "perdarahan_hamil")}
                  {yn("Ketuban pecah dini", "ketuban_pecah_dini")}
                  {yn("Merokok selama hamil", "merokok")}
                  {yn("Paparan asap rokok", "paparan_asap_rokok")}
                  {yn("Mengonsumsi alkohol", "konsumsi_alkohol")}
                  {yn("Menggunakan obat tertentu", "obat_tertentu")}
                </div>
                {mstr("Keterangan obat tertentu", "obat_tertentu_ket", "Jika ya, sebutkan")}
              </div>

              {/* D. Riwayat Persalinan */}
              <div className="flex flex-col gap-3 border-t border-line pt-4">
                <p className="text-[13px] font-bold text-ink">D. Riwayat Persalinan</p>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Tanggal persalinan"><input type="date" className="input" value={mat.tanggal_persalinan}
                    onChange={(e) => setMat((s) => ({ ...s, tanggal_persalinan: e.target.value }))} /></Field>
                  <Field label="Jenis persalinan">
                    <Select value={mat.jenis_persalinan} onChange={(e) => setMat((s) => ({ ...s, jenis_persalinan: e.target.value }))}>
                      <option value="">—</option>
                      {JENIS_PERSALINAN.map((j) => <option key={j.value} value={j.value}>{j.label}</option>)}
                    </Select>
                  </Field>
                  {mstr("Tempat persalinan", "tempat_persalinan")}
                  {mnum("Skor APGAR menit ke-1", "apgar_menit_1", "0–10")}
                  {mnum("Skor APGAR menit ke-5", "apgar_menit_5", "0–10")}
                </div>
                <Field label="Indikasi persalinan prematur">
                  <CheckboxGroup options={INDIKASI_PREMATUR} value={mat.indikasi_prematur}
                    onChange={(v) => setMat((s) => ({ ...s, indikasi_prematur: v }))} />
                </Field>
                {mstr("Indikasi prematur lainnya", "indikasi_prematur_lainnya")}
                <Field label="Komplikasi persalinan">
                  <CheckboxGroup options={KOMPLIKASI_PERSALINAN} value={mat.komplikasi_persalinan}
                    onChange={(v) => setMat((s) => ({ ...s, komplikasi_persalinan: v }))} />
                </Field>
                {mstr("Komplikasi lainnya", "komplikasi_lainnya")}
              </div>

              {/* E. Kondisi Ibu Setelah Melahirkan */}
              <div className="flex flex-col gap-3 border-t border-line pt-4">
                <p className="text-[13px] font-bold text-ink">E. Kondisi Ibu Setelah Melahirkan</p>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Kondisi umum ibu">
                    <Select value={mat.kondisi_umum} onChange={(e) => setMat((s) => ({ ...s, kondisi_umum: e.target.value }))}>
                      <option value="">—</option>
                      {KONDISI_UMUM.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
                    </Select>
                  </Field>
                  {yn("Masih dirawat", "masih_dirawat")}
                  {yn("Mengalami komplikasi postpartum", "komplikasi_postpartum")}
                  {yn("Dapat berjalan", "dapat_berjalan")}
                  {yn("Dapat menyusui langsung", "dapat_menyusui")}
                </div>
              </div>
            </div>
          )}
        </Card>

        {mutation.isError && <Banner kind="error">Gagal menyimpan: {errorMessage(mutation.error)}</Banner>}

        <div className="flex justify-end">
          <SubmitButton loading={mutation.isPending} disabled={!valid}>Daftarkan Bayi</SubmitButton>
        </div>
      </form>
    </div>
  );
}
