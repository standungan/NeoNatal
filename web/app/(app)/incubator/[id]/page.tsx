"use client";

import Link from "next/link";
import { MenuAksiTabs } from "@/components/menu-aksi";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  BabyDetail,
  IncubatorDetail,
  IncubatorPlacement,
  ObservationRecord,
} from "@/lib/types";
import { Card, StatusBadge, PageState, BackLink, SectionTitle } from "@/components/ui";
import { formatDate, formatDateTime, genderLabel, canWrite } from "@/lib/format";
import { useAuth } from "@/components/providers";
import { ObservationSummaryCard } from "@/components/observation";
import { errorMessage } from "@/components/form";
import { IncubatorThresholdsCard } from "@/components/incubator-thresholds";
import { DeviceCard } from "@/components/device-card";
import { SensorChartCard } from "@/components/sensor-chart";
import { AlertFeedCard } from "@/components/alert-feed";

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
  const isAdmin = role === "admin";

  const incQ = useQuery({
    queryKey: ["incubator", id],
    queryFn: async () => (await api.get<IncubatorDetail>(`/incubators/${id}`)).data,
  });

  const placementsQ = useQuery({
    queryKey: ["placements", id],
    queryFn: async () =>
      (await api.get<IncubatorPlacement[]>(`/incubators/${id}/placements`)).data,
  });

  const babyId = incQ.data?.current_baby?.baby_id;
  const archived = !!incQ.data?.archived_at;

  const refreshAll = () => {
    qc.invalidateQueries({ queryKey: ["dashboard"] });
    qc.invalidateQueries({ queryKey: ["incubator", id] });
    qc.invalidateQueries({ queryKey: ["incubators"] });
    qc.invalidateQueries({ queryKey: ["placements", id] });
  };

  const discharge = useMutation({
    mutationFn: async () => api.post(`/babies/${babyId}/discharge`),
    onSuccess: () => {
      refreshAll();
      router.push("/dashboard");
    },
  });

  // Admin-only: change status between kosong/tidak_tersedia, delete an unused
  // incubator, or archive one that has held a baby.
  const setStatus = useMutation({
    mutationFn: async (status: string) => api.put(`/incubators/${id}`, { status }),
    onSuccess: refreshAll,
  });

  const remove = useMutation({
    mutationFn: async () => api.delete(`/incubators/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      router.push("/dashboard");
    },
  });

  // Archive keeps the page: it now shows the archived banner and the history.
  const archive = useMutation({
    mutationFn: async () => api.post(`/incubators/${id}/archive`),
    onSuccess: refreshAll,
  });

  const restore = useMutation({
    mutationFn: async () => api.post(`/incubators/${id}/restore`),
    onSuccess: refreshAll,
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

  // The sensor chart and alert feed cover only the current occupancy; say so,
  // or an emptied chart right after an admission reads as lost data.
  const lastStay = placementsQ.data?.find((p) => p.status === "discharged");
  const periodStart = incQ.data?.current_baby?.assigned_at ?? lastStay?.discharged_at ?? undefined;
  const periodNote = incQ.data?.current_baby
    ? `Sejak ${incQ.data.current_baby.baby_name} masuk, ${formatDateTime(incQ.data.current_baby.assigned_at)}.`
    : lastStay?.discharged_at
      ? `Sejak inkubator kosong, ${formatDateTime(lastStay.discharged_at)}. Data bayi sebelumnya ada di riwayat masing-masing bayi (lihat Riwayat Penggunaan).`
      : undefined;

  return (
    <div>
      {archived ? (
        <BackLink href="/admin/incubators" label="Kembali ke Arsip Inkubator" />
      ) : (
        <BackLink href="/dashboard" label="Kembali ke Dashboard" />
      )}
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
                {archived ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-kosong/15 px-2.5 py-1 text-xs font-bold text-muted">
                    📦 Diarsipkan
                  </span>
                ) : (
                  <StatusBadge status={incQ.data.status} />
                )}
              </div>
            </Card>

            {archived && (
              <Card className="border-kosong/40 bg-surface p-5">
                <p className="text-sm font-bold text-ink">
                  Inkubator ini diarsipkan pada {formatDateTime(incQ.data.archived_at!)}.
                </p>
                <p className="mt-1.5 text-[13px] leading-relaxed text-muted">
                  Inkubator tidak tampil di dashboard dan tidak bisa dipilih untuk bayi
                  baru. Riwayat penggunaannya tetap tersimpan di bawah; data sensor dan
                  peringatan tiap bayi ada di laporan bayi masing-masing.
                </p>
                {isAdmin && (
                  <div className="mt-4">
                    <button
                      type="button"
                      disabled={restore.isPending}
                      onClick={() => {
                        if (
                          confirm(
                            `Pulihkan Inkubator ${incQ.data!.incubator_no}?\n\n` +
                              "Inkubator kembali tampil di dashboard dengan status Tidak Tersedia. " +
                              "Tandai Kosong setelah siap dipakai (dan pasang ulang perangkat IoT bila perlu).",
                          )
                        ) {
                          restore.mutate();
                        }
                      }}
                      className="inline-flex items-center gap-2 rounded-xl border border-line bg-card px-4 py-2.5 text-sm font-bold text-ink hover:bg-surface disabled:opacity-60"
                    >
                      ↩️ Pulihkan Inkubator
                    </button>
                    {restore.isError && (
                      <p className="mt-3 text-sm font-semibold text-danger">
                        {errorMessage(restore.error)}
                      </p>
                    )}
                  </div>
                )}
              </Card>
            )}

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
              !archived && (
                <Card className="flex flex-col items-center gap-2 p-8 text-muted">
                  <span className="text-3xl">🛏️</span>
                  <p className="font-semibold">
                    Inkubator {incQ.data.incubator_no} kosong
                  </p>
                </Card>
              )
            )}

            {latestObservation && <ObservationSummaryCard record={latestObservation} />}

            {isAdmin && !babyId && !archived && (
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
                  {/* Never used → can be deleted for good. Used → only archived, so
                      the babies' placements, sensor data and alerts stay attached. */}
                  {!incQ.data.has_history &&
                    (MANUAL_STATUSES as readonly string[]).includes(incQ.data.status) && (
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
                  {incQ.data.has_history && (
                    <button
                      type="button"
                      disabled={archive.isPending}
                      onClick={() => {
                        if (
                          confirm(
                            `Arsipkan Inkubator ${incQ.data!.incubator_no}?\n\n` +
                              "Inkubator hilang dari dashboard dan tidak bisa dipilih untuk bayi baru; " +
                              "perangkat IoT-nya dilepas. Riwayat penempatan, data sensor, dan " +
                              "peringatan bayi-bayi yang pernah memakainya tetap tersimpan. " +
                              "Bisa dipulihkan kapan saja dari Arsip Inkubator.",
                          )
                        ) {
                          archive.mutate();
                        }
                      }}
                      className="inline-flex items-center gap-2 rounded-xl border border-line px-4 py-2.5 text-sm font-bold text-ink hover:bg-surface disabled:opacity-60"
                    >
                      📦 Arsipkan Inkubator
                    </button>
                  )}
                </div>
                {incQ.data.has_history && (
                  <p className="mt-3 text-[12.5px] leading-relaxed text-muted">
                    Inkubator ini pernah ditempati bayi, jadi tidak dihapus melainkan
                    diarsipkan — riwayat perawatan bayi-bayi itu tetap utuh.
                  </p>
                )}
                {[setStatus, remove, archive].map(
                  (m, i) =>
                    m.isError && (
                      <p key={i} className="mt-3 text-sm font-semibold text-danger">
                        {errorMessage(m.error)}
                      </p>
                    ),
                )}
              </Card>
            )}

            {!archived && (
              <>
                {/* Visible to every role: a nurse needs to know whether the
                    vitals feed is live. Provision/revoke inside are admin-only. */}
                <DeviceCard incubatorId={id} />

                <SensorChartCard incubatorId={id} periodNote={periodNote} since={periodStart} />

                <AlertFeedCard incubatorId={id} />
              </>
            )}

            {incQ.data.has_history && (
              <PlacementHistoryCard
                placements={placementsQ.data}
                loading={placementsQ.isLoading}
              />
            )}

            {isAdmin && !archived && <IncubatorThresholdsCard incubatorId={id} />}
          </div>
        )}
      </PageState>
    </div>
  );
}

/**
 * Who has used this incubator, and when. Each stay links to that baby's report,
 * where their sensor data and alerts from the stay are kept.
 */
function PlacementHistoryCard({
  placements,
  loading,
}: {
  placements?: IncubatorPlacement[];
  loading: boolean;
}) {
  return (
    <Card className="p-5">
      <SectionTitle>Riwayat Penggunaan</SectionTitle>
      {loading || !placements ? (
        <p className="mt-3 text-sm text-muted">Memuat…</p>
      ) : (
        <ul className="mt-3 divide-y divide-line">
          {placements.map((p) => (
            <li key={p.assignment_id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2.5">
              <div className="min-w-0 flex-1">
                <Link
                  href={`/baby/${p.baby_id}/report`}
                  className="text-[13.5px] font-bold text-primary hover:underline"
                >
                  {p.baby_name}
                </Link>
                <p className="text-[12px] text-muted">
                  {p.no_registrasi_nicu ?? "—"} · masuk {formatDateTime(p.assigned_at)}
                  {p.discharged_at ? ` · pulang ${formatDateTime(p.discharged_at)}` : ""}
                </p>
              </div>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11.5px] font-bold ${
                  p.status === "active" ? "bg-primary/10 text-primary" : "bg-kosong/15 text-muted"
                }`}
              >
                {p.status === "active" ? "Dirawat" : "Pulang"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
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
