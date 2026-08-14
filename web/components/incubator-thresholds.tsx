"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IncubatorThresholds } from "@/lib/types";
import { Card, PageState, SectionTitle, Spinner } from "@/components/ui";
import { errorMessage } from "@/components/form";

type Bounds = Record<string, { min: string; max: string }>;

/**
 * Admin-only editor for a single incubator's sensor alert thresholds.
 * UX gating only — the real boundary is the backend's AdminOnly guard on
 * PUT /incubators/{id}/thresholds.
 */
export function IncubatorThresholdsCard({ incubatorId }: { incubatorId: string }) {
  const qc = useQueryClient();
  const [bounds, setBounds] = useState<Bounds>({});
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const q = useQuery({
    queryKey: ["thresholds", incubatorId],
    queryFn: async () =>
      (await api.get<IncubatorThresholds>(`/incubators/${incubatorId}/thresholds`)).data,
  });

  useEffect(() => {
    if (!q.data) return;
    const b: Bounds = {};
    for (const m of q.data.metrics) {
      b[m.key] = { min: m.min?.toString() ?? "", max: m.max?.toString() ?? "" };
    }
    setBounds(b);
  }, [q.data]);

  const save = useMutation({
    mutationFn: async () => {
      const thresholds: Record<string, { min: number | null; max: number | null }> = {};
      for (const [key, v] of Object.entries(bounds)) {
        thresholds[key] = {
          min: v.min === "" ? null : Number(v.min),
          max: v.max === "" ? null : Number(v.max),
        };
      }
      return api.put(`/incubators/${incubatorId}/thresholds`, { thresholds });
    },
    onSuccess: () => {
      setErr(null);
      setSaved(true);
      qc.invalidateQueries({ queryKey: ["thresholds", incubatorId] });
      setTimeout(() => setSaved(false), 2000);
    },
    onError: (e) => setErr(errorMessage(e)),
  });

  const setField = (key: string, side: "min" | "max", val: string) =>
    setBounds((b) => ({ ...b, [key]: { ...b[key], [side]: val } }));

  return (
    <Card className="p-5">
      <SectionTitle>Ambang Batas Sensor (Admin)</SectionTitle>
      <p className="mt-1 text-xs text-muted">
        Batas minimum/maksimum tiap sensor untuk memicu peringatan. Kosongkan untuk
        menonaktifkan salah satu batas.
      </p>
      <PageState loading={q.isLoading} error={q.error} onRetry={() => q.refetch()}>
        {q.data && (
          <div className="mt-4 flex flex-col gap-2.5">
            {q.data.metrics.map((m) => (
              <div key={m.key} className="flex items-center gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-semibold text-ink">{m.label}</p>
                  <p className="text-[11px] text-muted">{m.unit}</p>
                </div>
                <input
                  type="number"
                  step="any"
                  className="w-20 rounded-lg border border-line px-2 py-1.5 text-center text-sm outline-none focus:border-primary"
                  placeholder="min"
                  value={bounds[m.key]?.min ?? ""}
                  onChange={(e) => setField(m.key, "min", e.target.value)}
                />
                <span className="text-muted">–</span>
                <input
                  type="number"
                  step="any"
                  className="w-20 rounded-lg border border-line px-2 py-1.5 text-center text-sm outline-none focus:border-primary"
                  placeholder="max"
                  value={bounds[m.key]?.max ?? ""}
                  onChange={(e) => setField(m.key, "max", e.target.value)}
                />
              </div>
            ))}
            {err && <p className="text-[13px] text-danger">{err}</p>}
            <div className="mt-1 flex items-center justify-end gap-3">
              {saved && <span className="text-[13px] font-semibold text-ok">Tersimpan ✓</span>}
              {!q.data.is_custom && !saved && (
                <span className="text-[11px] text-muted">Memakai nilai default</span>
              )}
              <button
                onClick={() => save.mutate()}
                disabled={save.isPending}
                className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
              >
                {save.isPending && <Spinner className="h-4 w-4" />} Simpan Ambang Batas
              </button>
            </div>
          </div>
        )}
      </PageState>
    </Card>
  );
}
