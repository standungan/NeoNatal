"use client";

import { MenuAksiTabs } from "@/components/menu-aksi";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { BabyDetail, IncubatorDetail, ObservationRecord } from "@/lib/types";
import { Card, StatusBadge, PageState, BackLink, SectionTitle } from "@/components/ui";
import { formatDate, formatDateTime, genderLabel, canWrite } from "@/lib/format";
import { useAuth } from "@/components/providers";
import { ObservationSummaryCard } from "@/components/observation";
import { errorMessage } from "@/components/form";
import { IncubatorThresholdsCard } from "@/components/incubator-thresholds";

// Statuses an admin may set by hand (occupied/warning are system-managed).
const MANUAL_STATUSES = ["kosong", "tidak_tersedia"] as const;
const STATUS_ACTION_LABEL: Record<string, string> = {
  kosong: "✅ Tandai Kosong",
  tidak_tersedia: "🚫 Tandai Tidak Tersedia",
};

export default function IncubatorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { role } = useAuth();
  const writable = canWrite(role);

  const incQ = useQuery({
    queryKey: ["incubator", id],
    queryFn: async () => (await api.get<IncubatorDetail>(`/incubators/${id}`)).data,
  });

  const babyId = incQ.data?.current_baby?.baby_id;

  const discharge = useMutation({
    mutationFn: async () => api.post(`/babies/${babyId}/discharge`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["incubator", id] });
      router.push("/dashboard");
    },
  });

  // Admin-only: change status between kosong/tidak_tersedia, or delete an unused incubator.
  const setStatus = useMutation({
    mutationFn: async (status: string) => api.put(`/incubators/${id}`, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["incubator", id] });
    },
  });

  const remove = useMutation({
    mutationFn: async () => api.delete(`/incubators/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      router.push("/dashboard");
    },
  });

  const babyQ = useQuery({
    queryKey: ["baby", babyId],
    enabled: !!babyId,
    queryFn: async () => (await api.get<BabyDetail>(`/babies/${babyId}`)).data,
  });

  const observationQ = useQuery({
    queryKey: ["observation", babyId],
    enabled: !!babyId,
    queryFn: async () =>
      (await api.get<ObservationRecord[]>(`/babies/${babyId}/observation?limit=1`)).data,
  });
  const latestObservation = observationQ.data?.[0];

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

            {babyId && (
              <Card className="p-5">
                <SectionTitle>Menu Aksi</SectionTitle>
                <div className="mt-4 flex flex-col gap-3">
                  <MenuAksiTabs babyId={babyId} />
                  {writable && (
                    <div>
                      <button
                        type="button"
                        disabled={discharge.isPending}
                        onClick={() => {
                          if (confirm("Pulangkan bayi ini? Inkubator akan dikosongkan.")) {
                            discharge.mutate();
                          }
                        }}
                        className="inline-flex items-center gap-2 rounded-xl border border-danger/30 px-4 py-2.5 text-sm font-bold text-danger hover:bg-danger/10 disabled:opacity-60"
                      >
                        🏠 Pulangkan
                      </button>
                    </div>
                  )}
                </div>
                {discharge.isError && (
                  <p className="mt-3 text-sm font-semibold text-danger">Gagal memulangkan bayi.</p>
                )}
              </Card>
            )}

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

            {latestObservation && <ObservationSummaryCard record={latestObservation} />}

            {role === "admin" && !babyId && (
              <Card className="p-5">
                <SectionTitle>Pengaturan Inkubator (Admin)</SectionTitle>
                <div className="mt-4 flex flex-wrap gap-2.5">
                  {MANUAL_STATUSES.filter((s) => s !== incQ.data!.status).map((s) => (
                    <button
                      key={s}
                      type="button"
                      disabled={setStatus.isPending}
                      onClick={() => setStatus.mutate(s)}
                      className="inline-flex items-center gap-2 rounded-xl border border-line px-4 py-2.5 text-sm font-bold text-ink hover:bg-surface disabled:opacity-60"
                    >
                      {STATUS_ACTION_LABEL[s]}
                    </button>
                  ))}
                  {(MANUAL_STATUSES as readonly string[]).includes(incQ.data!.status) && (
                    <button
                      type="button"
                      disabled={remove.isPending}
                      onClick={() => {
                        if (
                          confirm(
                            `Hapus Inkubator ${incQ.data!.incubator_no}? Tindakan ini tidak dapat dibatalkan.`,
                          )
                        ) {
                          remove.mutate();
                        }
                      }}
                      className="inline-flex items-center gap-2 rounded-xl border border-danger/30 px-4 py-2.5 text-sm font-bold text-danger hover:bg-danger/10 disabled:opacity-60"
                    >
                      🗑️ Hapus Inkubator
                    </button>
                  )}
                </div>
                {setStatus.isError && (
                  <p className="mt-3 text-sm font-semibold text-danger">
                    {errorMessage(setStatus.error)}
                  </p>
                )}
                {remove.isError && (
                  <p className="mt-3 text-sm font-semibold text-danger">
                    {errorMessage(remove.error)}
                  </p>
                )}
              </Card>
            )}

            {role === "admin" && <IncubatorThresholdsCard incubatorId={id} />}
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
