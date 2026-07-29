"use client";

import type { ReactNode } from "react";
import type { AssignmentInfo, BabyDetail, MaternalRecord } from "@/lib/types";
import { Card, SectionTitle } from "@/components/ui";
import { formatDate, formatDateTime } from "@/lib/format";
import { PENDIDIKAN, JENIS_PERSALINAN, KONDISI_UMUM, JENIS_KEHAMILAN } from "@/lib/intake";

const labelOf = (opts: { value: string; label: string }[], v: string | null) =>
  v ? opts.find((o) => o.value === v)?.label ?? v : "-";

const hhmm = (t: string | null) => (t ? t.slice(0, 5) : "-");

/** Label/value grid for read-only info. */
function DL({ items }: { items: [string, ReactNode][] }) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 sm:grid-cols-3">
      {items.map(([label, value]) => (
        <div key={label}>
          <div className="text-[11px] text-muted">{label}</div>
          <div className="text-[13px] font-semibold text-ink">{value ?? "-"}</div>
        </div>
      ))}
    </div>
  );
}

/** Compact grid of Ya/Tidak facts. */
function BoolGrid({ rows }: { rows: [string, boolean | null][] }) {
  return (
    <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
      {rows.map(([label, v]) => (
        <div key={label} className="flex items-center justify-between gap-2 rounded-lg bg-[#f8fafc] px-3 py-1.5">
          <span className="text-[12.5px] text-ink">{label}</span>
          <span className={`shrink-0 text-[12px] font-bold ${v == null ? "text-muted" : "text-ink"}`}>
            {v == null ? "-" : v ? "Ya" : "Tidak"}
          </span>
        </div>
      ))}
    </div>
  );
}

function Chips({ items }: { items: string[] | null }) {
  if (!items || items.length === 0) return <span className="text-[13px] text-muted">-</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((it) => (
        <span key={it} className="rounded-md bg-primary/10 px-2 py-0.5 text-[12px] font-medium text-primary">
          {it}
        </span>
      ))}
    </div>
  );
}

function SubHead({ children }: { children: ReactNode }) {
  return <p className="text-[13px] font-bold text-ink">{children}</p>;
}

// ── Data Registrasi (from the active assignment) ──────────────────────────────
export function RegistrationCard({ assignment }: { assignment: AssignmentInfo }) {
  return (
    <Card className="p-5">
      <SectionTitle>Data Registrasi</SectionTitle>
      <div className="mt-4">
        <DL
          items={[
            ["No. Registrasi NICU", assignment.no_registrasi_nicu ?? "-"],
            ["Tanggal Masuk NICU", formatDateTime(assignment.assigned_at)],
            ["Rumah Sakit", assignment.rumah_sakit ?? "-"],
            ["Ruang NICU", assignment.ruang_nicu ?? "-"],
            ["Inkubator", `No. ${assignment.incubator_no}${assignment.location ? ` — ${assignment.location}` : ""}`],
            ["DPJP", assignment.dpjp_name ?? "-"],
            ["Perawat Penerima", assignment.assigned_by_name ?? "-"],
          ]}
        />
      </div>
    </Card>
  );
}

// ── Identitas Bayi (extended) ─────────────────────────────────────────────────
export function BabyIdentityCard({ baby }: { baby: BabyDetail }) {
  return (
    <Card className="p-5">
      <SectionTitle>Identitas Bayi</SectionTitle>
      <div className="mt-4">
        <DL
          items={[
            ["No. Rekam Medis", baby.no_rm_bayi ?? "-"],
            ["Golongan Darah", baby.golongan_darah ?? "-"],
            ["Tanggal Lahir", formatDate(baby.birth_date)],
            ["Jam Lahir", hhmm(baby.jam_lahir)],
            ["Usia Gestasi", baby.gestational_age != null ? `${baby.gestational_age} mgg` : "-"],
            ["Usia Masuk NICU", baby.usia_masuk_nicu_jam != null ? `${baby.usia_masuk_nicu_jam} jam` : "-"],
            ["Berat Lahir", baby.birth_weight != null ? `${baby.birth_weight} gram` : "-"],
            ["Panjang Lahir", baby.birth_length != null ? `${baby.birth_length} cm` : "-"],
            ["Lingkar Kepala", baby.lingkar_kepala != null ? `${baby.lingkar_kepala} cm` : "-"],
            ["Lingkar Dada", baby.lingkar_dada != null ? `${baby.lingkar_dada} cm` : "-"],
            ["Jenis Kelahiran", baby.birth_type ?? "-"],
          ]}
        />
      </div>
    </Card>
  );
}

// ── Rekam Medis Ibu (A–E) ─────────────────────────────────────────────────────
export function MaternalRecordCard({ maternal: m, parent }: {
  maternal: MaternalRecord;
  parent: BabyDetail["parent"];
}) {
  return (
    <Card className="flex flex-col gap-5 p-5">
      <SectionTitle>Rekam Medis Ibu</SectionTitle>

      {/* A. Identitas Ibu */}
      <div className="flex flex-col gap-3">
        <SubHead>A. Identitas Ibu</SubHead>
        <DL
          items={[
            ["Nama Ibu", parent?.mother_name ?? "-"],
            ["No. Telepon", parent?.mother_phone ?? "-"],
            ["No. Rekam Medis Ibu", m.no_rm_ibu ?? "-"],
            ["Umur", m.umur_ibu != null ? `${m.umur_ibu} th` : "-"],
            ["Pendidikan", labelOf(PENDIDIKAN, m.pendidikan)],
            ["Pekerjaan", m.pekerjaan ?? "-"],
            ["Golongan Darah", m.golongan_darah ?? "-"],
            ["Alamat", m.alamat ?? "-"],
          ]}
        />
      </div>

      {/* B. Riwayat Obstetri */}
      <div className="flex flex-col gap-3 border-t border-line pt-4">
        <SubHead>B. Riwayat Obstetri</SubHead>
        <DL
          items={[
            ["Kehamilan ke-", m.kehamilan_ke ?? "-"],
            ["Jumlah Persalinan Hidup", m.jumlah_persalinan_hidup ?? "-"],
          ]}
        />
        <BoolGrid
          rows={[
            ["Riwayat abortus", m.riwayat_abortus],
            ["Riwayat persalinan prematur", m.riwayat_prematur],
            ["Riwayat bayi BBLR", m.riwayat_bblr],
            ["Riwayat bayi meninggal", m.riwayat_bayi_meninggal],
          ]}
        />
      </div>

      {/* C. Riwayat Kehamilan */}
      <div className="flex flex-col gap-3 border-t border-line pt-4">
        <SubHead>C. Riwayat Kehamilan Saat Ini</SubHead>
        <DL
          items={[
            ["Usia kehamilan lahir", m.usia_kehamilan_lahir != null ? `${m.usia_kehamilan_lahir} mgg` : "-"],
            ["Kehamilan", labelOf(JENIS_KEHAMILAN, m.jenis_kehamilan)],
            ["Jumlah kunjungan ANC", m.jumlah_anc ?? "-"],
          ]}
        />
        <BoolGrid
          rows={[
            ["Rutin ANC", m.anc_rutin],
            ["Hipertensi kehamilan", m.hipertensi_kehamilan],
            ["Preeklamsia", m.preeklamsia],
            ["Diabetes gestasional", m.diabetes_gestasional],
            ["Infeksi selama hamil", m.infeksi_hamil],
            ["Perdarahan selama kehamilan", m.perdarahan_hamil],
            ["Ketuban pecah dini", m.ketuban_pecah_dini],
            ["Merokok selama hamil", m.merokok],
            ["Paparan asap rokok", m.paparan_asap_rokok],
            ["Mengonsumsi alkohol", m.konsumsi_alkohol],
            ["Menggunakan obat tertentu", m.obat_tertentu],
          ]}
        />
        {m.obat_tertentu_ket && (
          <p className="text-[12.5px] text-muted">Ket. obat: <span className="text-ink">{m.obat_tertentu_ket}</span></p>
        )}
      </div>

      {/* D. Riwayat Persalinan */}
      <div className="flex flex-col gap-3 border-t border-line pt-4">
        <SubHead>D. Riwayat Persalinan</SubHead>
        <DL
          items={[
            ["Tanggal persalinan", m.tanggal_persalinan ? formatDate(m.tanggal_persalinan) : "-"],
            ["Jenis persalinan", labelOf(JENIS_PERSALINAN, m.jenis_persalinan)],
            ["Tempat persalinan", m.tempat_persalinan ?? "-"],
            ["APGAR menit 1", m.apgar_menit_1 ?? "-"],
            ["APGAR menit 5", m.apgar_menit_5 ?? "-"],
          ]}
        />
        <div>
          <div className="mb-1.5 text-[11px] text-muted">Indikasi persalinan prematur</div>
          <Chips items={m.indikasi_prematur} />
          {m.indikasi_prematur_lainnya && (
            <p className="mt-1 text-[12.5px] text-muted">Lainnya: <span className="text-ink">{m.indikasi_prematur_lainnya}</span></p>
          )}
        </div>
        <div>
          <div className="mb-1.5 text-[11px] text-muted">Komplikasi persalinan</div>
          <Chips items={m.komplikasi_persalinan} />
          {m.komplikasi_lainnya && (
            <p className="mt-1 text-[12.5px] text-muted">Lainnya: <span className="text-ink">{m.komplikasi_lainnya}</span></p>
          )}
        </div>
      </div>

      {/* E. Kondisi Ibu Setelah Melahirkan */}
      <div className="flex flex-col gap-3 border-t border-line pt-4">
        <SubHead>E. Kondisi Ibu Setelah Melahirkan</SubHead>
        <DL items={[["Kondisi umum", labelOf(KONDISI_UMUM, m.kondisi_umum)]]} />
        <BoolGrid
          rows={[
            ["Masih dirawat", m.masih_dirawat],
            ["Komplikasi postpartum", m.komplikasi_postpartum],
            ["Dapat berjalan", m.dapat_berjalan],
            ["Dapat menyusui langsung", m.dapat_menyusui],
          ]}
        />
      </div>
    </Card>
  );
}
