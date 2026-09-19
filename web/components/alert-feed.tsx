"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/components/providers";
import { errorMessage } from "@/components/form";
import { Card, SectionTitle, Spinner } from "@/components/ui";
import { canWrite, formatDate } from "@/lib/format";
import { ALERT_LABELS, type SensorAlert } from "@/lib/types";

/**
 * Alert feed — for one incubator, or for one baby.
 *
 * The engine writes `sensor_alerts` rows and flips `incubators.status`, but a
 * status badge says only "something is wrong" — this says which metric, what it
 * read, which bound it crossed, and when. An alarm nobody can interpret is
 * barely better than no alarm.
 *
 * `incubatorId`: the incubator's CURRENT occupancy only (the backend cuts it at
 * the present baby's admission, or the last discharge) — the previous baby's
 * alarms are theirs, not the next baby's.
 * `babyId`: every alarm raised while that baby was in an incubator, wherever,
 * which is how they stay readable after discharge.
 *
 * Visible to every role; acknowledging is PerawatOrAdmin, matching the backend.
 */
export function AlertFeedCard(
  props: { incubatorId: string; babyId?: never } | { babyId: string; incubatorId?: never },
) {
  const qc = useQueryClient();
  const { role } = useAuth();
  const writable = canWrite(role);

  const forBaby = props.babyId !== undefined;
  const key = forBaby ? ["alerts", "baby", props.babyId] : ["alerts", props.incubatorId];
  const path = forBaby
    ? `/babies/${props.babyId}/alerts?limit=100`
    : `/incubators/${props.incubatorId}/alerts?limit=20`;

  const q = useQuery({
    queryKey: key,
    queryFn: async () => (await api.get<SensorAlert[]>(path)).data,
    // An alert can open between page loads; the chart polls, so should this.
    refetchInterval: 15_000,
  });

  const ack = useMutation({
    mutationFn: async (alertId: string) =>
      api.post(`/alerts/${alertId}/acknowledge`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: key });
      if (props.incubatorId) {
        qc.invalidateQueries({ queryKey: ["incubator", props.incubatorId] });
      }
    },
  });

  if (q.isLoading) {
    return (
      <Card className="p-5">
        <SectionTitle>Riwayat Peringatan</SectionTitle>
        <div className="flex justify-center py-6">
          <Spinner />
        </div>
      </Card>
    );
  }

  const alerts = q.data ?? [];
  const open = alerts.filter((a) => !a.resolved_at);

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <SectionTitle>Riwayat Peringatan</SectionTitle>
        {open.length > 0 && (
          <span className="rounded-full bg-danger/10 px-2.5 py-0.5 text-[12px] font-bold text-danger">
            {open.length} aktif
          </span>
        )}
      </div>

      {alerts.length === 0 ? (
        <p className="mt-2 text-sm text-muted">
          {forBaby
            ? "Tidak ada peringatan sensor selama bayi ini dirawat."
            : "Belum ada peringatan sejak periode ini dimulai."}
        </p>
      ) : (
        <ul className="mt-3 flex flex-col gap-2">
          {alerts.map((a) => (
            <AlertRow
              key={a.alert_id}
              alert={a}
              forBaby={forBaby}
              // A baby's history is a record: acknowledging an alarm that has
              // already closed — usually because the baby went home — says nothing.
              canAck={writable && (!forBaby || !a.resolved_at)}
              onAck={() => ack.mutate(a.alert_id)}
              acking={ack.isPending && ack.variables === a.alert_id}
            />
          ))}
        </ul>
      )}

      {ack.error && (
        <p className="mt-2 text-sm font-semibold text-danger">
          {errorMessage(ack.error)}
        </p>
      )}
    </Card>
  );
}

/** How an alert ended. Only a null reason means the readings recovered. */
const CLOSED_LABEL: Record<NonNullable<SensorAlert["resolved_reason"]>, string> = {
  discharged: "ditutup saat bayi pulang",
  archived: "ditutup saat inkubator diarsipkan",
};

function AlertRow({
  alert,
  forBaby,
  canAck,
  onAck,
  acking,
}: {
  alert: SensorAlert;
  forBaby: boolean;
  canAck: boolean;
  onAck: () => void;
  acking: boolean;
}) {
  const isOpen = !alert.resolved_at;
  const closedLabel = alert.resolved_reason ? CLOSED_LABEL[alert.resolved_reason] : "selesai";

  return (
    <li
      className={
        "rounded-xl border p-3 " +
        (isOpen ? "border-danger/30 bg-danger/5" : "border-line bg-surface")
      }
    >
      <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1.5">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-[13.5px] font-bold text-ink">
            <span
              aria-hidden
              className={
                "h-2 w-2 shrink-0 rounded-full " +
                (isOpen ? "bg-danger" : "bg-kosong")
              }
            />
            {ALERT_LABELS[alert.alert_type] ?? alert.alert_type}
            <span className="font-semibold text-muted">
              {isOpen ? "· aktif" : `· ${closedLabel}`}
            </span>
          </p>

          <p className="mt-1 text-[12.5px] text-muted">
            {/* The reading and the bound it crossed, as recorded at the time. */}
            {alert.metric_key} <strong className="text-ink">{alert.value}</strong>
            {alert.threshold != null && <> (batas {alert.threshold})</>}
            {forBaby
              ? alert.incubator_no && <> · Inkubator {alert.incubator_no}</>
              : alert.baby_name && <> · {alert.baby_name}</>}
          </p>

          <p className="mt-0.5 text-[11.5px] text-muted">
            mulai {formatDate(alert.started_at, true)}
            {alert.resolved_at && <> · {alert.resolved_reason ? "ditutup" : "selesai"} {formatDate(alert.resolved_at, true)}</>}
          </p>
        </div>

        <div className="shrink-0">
          {alert.acknowledged_at ? (
            <span className="text-[11.5px] text-muted">
              dilihat {alert.acknowledged_by_name ?? "—"}
            </span>
          ) : (
            canAck && (
              <button
                onClick={onAck}
                disabled={acking}
                className="flex items-center gap-1.5 rounded-lg border border-line bg-card px-3 py-1 text-[12.5px] font-bold text-ink hover:bg-surface disabled:opacity-60"
              >
                {acking && <Spinner className="h-3 w-3" />}
                Tandai dilihat
              </button>
            )
          )}
        </div>
      </div>

      {isOpen && alert.acknowledged_at && (
        <p className="mt-2 text-[11.5px] leading-relaxed text-muted">
          Sudah dilihat, tetapi <strong>masih aktif</strong> — peringatan hanya
          selesai ketika pembacaan sensor kembali normal.
        </p>
      )}
    </li>
  );
}
