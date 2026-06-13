"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { BabyDetail, IncubatorDetail } from "@/lib/types";
import { Card, StatusBadge, PageState, BackLink, SectionTitle } from "@/components/ui";
import { formatDate, formatDateTime, genderLabel } from "@/lib/format";

export default function IncubatorDetailPage() {
  const { id } = useParams<{ id: string }>();

  const incQ = useQuery({
    queryKey: ["incubator", id],
    queryFn: async () => (await api.get<IncubatorDetail>(`/incubators/${id}`)).data,
  });

  const babyId = incQ.data?.current_baby?.baby_id;

  const babyQ = useQuery({
    queryKey: ["baby", babyId],
    enabled: !!babyId,
    queryFn: async () => (await api.get<BabyDetail>(`/babies/${babyId}`)).data,
  });

  return (
    <div>
      <BackLink href="/dashboard" label="Kembali ke Dashboard" />
      <h1 className="mb-4 mt-3 text-xl font-extrabold text-ink">
        Detail Inkubator
      </h1>

      <PageState
        loading={incQ.isLoading}
        error={incQ.error}
        onRetry={() => incQ.refetch()}
      >
        {incQ.data && (
          <div className="flex flex-col gap-4">
            <Card className="p-5">
              <div className="flex items-center gap-3.5">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-lg font-extrabold text-primary">
                  {incQ.data.incubator_no}
                </div>
                <div className="flex-1">
                  <p className="text-base font-extrabold text-ink">
                    Inkubator {incQ.data.incubator_no}
                  </p>
                  {incQ.data.location && (
                    <p className="text-sm text-muted">{incQ.data.location}</p>
                  )}
                </div>
                <StatusBadge status={incQ.data.status} />
              </div>
            </Card>

            {babyId ? (
              <BabyCard baby={babyQ.data} loading={babyQ.isLoading} />
            ) : (
              <Card className="flex flex-col items-center gap-2 p-8 text-muted">
                <span className="text-3xl">🛏️</span>
                <p className="font-semibold">
                  Inkubator {incQ.data.incubator_no} kosong
                </p>
              </Card>
            )}

            {babyId && (
              <Card className="p-5">
                <SectionTitle>Menu</SectionTitle>
                <div className="mt-4">
                  <Link
                    href={`/baby/${babyId}/report`}
                    className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary-dark"
                  >
                    📊 Lihat Laporan & Tren Vital
                  </Link>
                </div>
              </Card>
            )}
          </div>
        )}
      </PageState>
    </div>
  );
}

function BabyCard({ baby, loading }: { baby?: BabyDetail; loading: boolean }) {
  if (loading || !baby) {
    return (
      <Card className="p-8 text-center text-muted">Memuat data bayi…</Card>
    );
  }
  const a = baby.current_assignment;
  return (
    <Card className="p-5">
      <SectionTitle>Informasi Bayi</SectionTitle>
      <dl className="mt-4 divide-y divide-line">
        <Row label="Nama" value={baby.baby_name} />
        <Row label="Jenis Kelamin" value={genderLabel(baby.gender)} />
        <Row label="Tanggal Lahir" value={formatDate(baby.birth_date)} />
        <Row label="Usia" value={`${baby.age_in_days} hari`} />
        <Row
          label="Berat Lahir"
          value={baby.birth_weight != null ? `${baby.birth_weight} gram` : "-"}
        />
        {a && (
          <>
            <Row
              label="Inkubator"
              value={`No. ${a.incubator_no}${a.location ? ` — ${a.location}` : ""}`}
            />
            <Row label="Tanggal Masuk" value={formatDateTime(a.assigned_at)} />
            {a.assigned_by_name && (
              <Row label="Perawat" value={a.assigned_by_name} />
            )}
          </>
        )}
        {baby.parent && (
          <>
            <Row label="Nama Ibu" value={baby.parent.mother_name ?? "-"} />
            <Row label="Nama Ayah" value={baby.parent.father_name ?? "-"} />
            <Row label="Telepon" value={baby.parent.mother_phone ?? "-"} />
          </>
        )}
      </dl>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-4 py-2.5">
      <dt className="w-32 shrink-0 text-[13px] text-muted">{label}</dt>
      <dd className="text-[13px] font-semibold text-ink">{value}</dd>
    </div>
  );
}
