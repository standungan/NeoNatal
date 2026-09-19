"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { Card, SectionTitle, Spinner } from "@/components/ui";
import type {
  BabySensorHistory,
  IncubatorThresholds,
  SensorHistoryPoint,
  ThresholdMetric,
} from "@/lib/types";

/**
 * One baby's sensor history across their whole stay.
 *
 * The incubator chart shows only the incubator's current occupancy; this is where
 * a baby's readings live once they have gone home, the incubator has taken the
 * next baby, or been archived. The backend buckets any stay into a few hundred
 * points, each carrying its mean (the line) and the min–max inside it (the pale
 * band) — a mean alone would hide a short desaturation.
 *
 * Time is a real numeric axis, not categories: a stretch with no data shows as a
 * gap of the right width instead of being squeezed out.
 */

const LINE = "#2563eb";

type Metric = "suhu_bayi" | "suhu_inkubator" | "heart_rate" | "spo2" | "kelembapan_inkubator";

const PANELS: { title: string; unit: string; key: Metric; celsius?: boolean }[] = [
  { title: "Suhu Bayi", unit: "°C", key: "suhu_bayi", celsius: true },
  { title: "Suhu Inkubator", unit: "°C", key: "suhu_inkubator", celsius: true },
  { title: "Detak Jantung", unit: "bpm", key: "heart_rate" },
  { title: "SpO₂", unit: "%", key: "spo2" },
  { title: "Kelembapan", unit: "%", key: "kelembapan_inkubator" },
];

type Row = { ts: number; v: number | null; band: [number, number] | null };

function rowsFor(points: SensorHistoryPoint[], key: Metric, bucketMinutes: number): Row[] {
  // Break the line wherever a stretch of buckets is missing, so two readings a
  // day apart are not joined by a confident straight line.
  const gapMs = Math.max(bucketMinutes * 2, 5) * 60_000;
  const out: Row[] = [];
  let prev: number | null = null;
  for (const p of points) {
    const ts = new Date(p.t).getTime();
    if (prev != null && ts - prev > gapMs) {
      out.push({ ts: prev + 1, v: null, band: null });
    }
    const lo = p[`${key}_min` as const];
    const hi = p[`${key}_max` as const];
    out.push({ ts, v: p[key], band: lo != null && hi != null ? [lo, hi] : null });
    prev = ts;
  }
  return out;
}

function celsiusDomain(points: SensorHistoryPoint[], bounds: ThresholdMetric[]): [number, number] | undefined {
  // Skin and air temperature share one scale, as on the live chart, so they can
  // be read against each other.
  const vals: number[] = [];
  for (const p of points) {
    for (const k of ["suhu_bayi", "suhu_inkubator"] as const) {
      for (const v of [p[`${k}_min` as const], p[`${k}_max` as const], p[k]]) {
        if (v != null) vals.push(v);
      }
    }
  }
  for (const b of bounds.filter((x) => x.key === "suhu_bayi" || x.key === "suhu_inkubator")) {
    if (b.min != null) vals.push(b.min);
    if (b.max != null) vals.push(b.max);
  }
  if (vals.length === 0) return undefined;
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const pad = Math.max((hi - lo) * 0.12, 0.5);
  return [Math.floor(lo - pad), Math.ceil(hi + pad)];
}

function tickLabel(ts: number, spanMs: number) {
  const d = new Date(ts);
  return spanMs > 36 * 3600_000
    ? d.toLocaleString("id-ID", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
    : d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
}

function bucketLabel(minutes: number) {
  if (minutes < 60) return `${minutes} menit`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h} jam ${m} menit` : `${h} jam`;
}

export function BabySensorHistoryCard({
  babyId,
  incubatorId,
}: {
  babyId: string;
  /** The placement's incubator, for its threshold bands. */
  incubatorId?: string;
}) {
  const q = useQuery({
    queryKey: ["sensor-history", babyId],
    queryFn: async () =>
      (await api.get<BabySensorHistory>(`/babies/${babyId}/sensor-history`)).data,
  });
  const thresholds = useQuery({
    queryKey: ["thresholds", incubatorId],
    enabled: !!incubatorId,
    queryFn: async () =>
      (await api.get<IncubatorThresholds>(`/incubators/${incubatorId}/thresholds`)).data,
  });

  if (q.isLoading) {
    return (
      <Card className="p-5">
        <SectionTitle>Riwayat Data Sensor</SectionTitle>
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      </Card>
    );
  }

  const points = q.data?.points ?? [];
  if (q.error || points.length === 0) {
    return (
      <Card className="p-5">
        <SectionTitle>Riwayat Data Sensor</SectionTitle>
        <p className="mt-2 text-sm text-muted">
          {q.error
            ? "Gagal memuat riwayat data sensor."
            : "Tidak ada data sensor yang tercatat untuk bayi ini."}
        </p>
      </Card>
    );
  }

  const bucket = q.data!.bucket_minutes;
  const bounds = thresholds.data?.metrics ?? [];
  const first = new Date(points[0].t).getTime();
  const last = new Date(points[points.length - 1].t).getTime();
  const span = last - first;
  const cDomain = celsiusDomain(points, bounds);
  const samples = points.reduce((n, p) => n + p.samples, 0);

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <SectionTitle>Riwayat Data Sensor</SectionTitle>
        <span className="text-xs text-muted">
          {samples.toLocaleString("id-ID")} pembacaan
        </span>
      </div>
      <p className="mt-1 text-xs text-muted">
        Seluruh masa rawat bayi ini, termasuk setelah inkubatornya dipakai bayi lain.
        Tiap titik = rata-rata {bucketLabel(bucket)}; pita pucat = nilai terendah–tertinggi di dalamnya.
      </p>

      <div className="mt-4 flex flex-col gap-5">
        {PANELS.map((p) => {
          const rows = rowsFor(points, p.key, bucket);
          const band = bounds.find((b) => b.key === p.key);
          const hasAny = rows.some((r) => r.v != null);
          return (
            // min-w-0: see SensorPanel — without it the page scrolls sideways on phones.
            <div key={p.key} className="min-w-0">
              <h4 className="mb-1 truncate text-[13.5px] font-bold text-ink">
                {p.title} <span className="font-medium text-muted">({p.unit})</span>
              </h4>
              {hasAny ? (
                <ResponsiveContainer width="100%" height={170}>
                  <ComposedChart data={rows} margin={{ top: 6, right: 12, bottom: 0, left: -12 }}>
                    <CartesianGrid stroke="#eef2f7" vertical={false} />
                    {band && (band.min != null || band.max != null) && (
                      <ReferenceArea
                        y1={band.min ?? undefined}
                        y2={band.max ?? undefined}
                        fill="#94a3b8"
                        fillOpacity={0.08}
                        ifOverflow="extendDomain"
                      />
                    )}
                    <XAxis
                      dataKey="ts"
                      type="number"
                      scale="time"
                      domain={[first, last]}
                      tickFormatter={(ts: number) => tickLabel(ts, span)}
                      tickCount={6}
                      tick={{ fontSize: 10, fill: "#94a3b8" }}
                      tickLine={false}
                      axisLine={false}
                      minTickGap={60}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: "#94a3b8" }}
                      tickLine={false}
                      axisLine={false}
                      width={42}
                      domain={p.celsius && cDomain ? cDomain : ["auto", "auto"]}
                      allowDecimals
                    />
                    <Tooltip
                      contentStyle={{ borderRadius: 12, border: "1px solid #e9eef5", fontSize: 12 }}
                      labelStyle={{ color: "#64748b", fontSize: 11 }}
                      labelFormatter={(ts) =>
                        new Date(Number(ts)).toLocaleString("id-ID", {
                          day: "2-digit", month: "short", year: "numeric",
                          hour: "2-digit", minute: "2-digit",
                        })
                      }
                      formatter={(v, name) => {
                        if (Array.isArray(v)) return [`${v[0]}–${v[1]} ${p.unit}`, "Rentang"];
                        return [v == null ? "—" : `${Math.round(Number(v) * 10) / 10} ${p.unit}`, name];
                      }}
                    />
                    <Area
                      dataKey="band"
                      name="Rentang"
                      stroke="none"
                      fill={LINE}
                      fillOpacity={0.12}
                      isAnimationActive={false}
                    />
                    <Line
                      dataKey="v"
                      name="Rata-rata"
                      stroke={LINE}
                      strokeWidth={2}
                      isAnimationActive={false}
                      // A lone bucket between gaps would be a zero-length path and
                      // vanish; mark only those, as the live chart does.
                      dot={(props) => {
                        const { cx, cy, index, key } = props as {
                          cx?: number; cy?: number; index: number; key?: string;
                        };
                        const has = (i: number) => i >= 0 && i < rows.length && rows[i].v != null;
                        if (cx == null || cy == null || has(index - 1) || has(index + 1)) {
                          return <g key={key} />;
                        }
                        return <circle key={key} cx={cx} cy={cy} r={2.5} fill={LINE} />;
                      }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-[170px] items-center justify-center rounded-xl bg-surface">
                  <p className="px-4 text-center text-[12px] text-muted">
                    Tidak ada nilai {p.title} selama bayi ini dirawat.
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
