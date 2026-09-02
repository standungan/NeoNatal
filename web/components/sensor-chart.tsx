"use client";

import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { useSensorReadings } from "@/hooks/use-sensor-readings";
import { Card, SectionTitle, Spinner } from "@/components/ui";
import type {
  IncubatorThresholds,
  SensorReading,
  ThresholdMetric,
} from "@/lib/types";

/**
 * Live sensor trends for one incubator, as small multiples.
 *
 * One metric, one unit, one axis per panel — never a dual-axis plot, where the
 * point at which two lines cross is an artefact of the two scales rather than
 * anything real.
 *
 * Skin and air temperature are separate panels but share a y-domain (see
 * scaleGroup): they are the same unit and are read against each other, so
 * letting each auto-scale would make a 0.3 °C wobble look like a 3 °C swing.
 */

const LINE = "#2563eb";

type Panel = {
  title: string;
  unit: string;
  dataKey: keyof SensorReading;
  /** threshold key whose min/max draws the acceptable band */
  thresholdKey?: string;
  /** panels sharing a group are drawn on one common y-domain */
  scaleGroup?: string;
};

const PANELS: Panel[] = [
  { title: "Suhu Bayi", unit: "°C", dataKey: "suhu_bayi", thresholdKey: "suhu_bayi", scaleGroup: "celsius" },
  { title: "Suhu Inkubator", unit: "°C", dataKey: "suhu_inkubator", thresholdKey: "suhu_inkubator", scaleGroup: "celsius" },
  { title: "Detak Jantung", unit: "bpm", dataKey: "heart_rate", thresholdKey: "heart_rate" },
  { title: "SpO₂", unit: "%", dataKey: "spo2", thresholdKey: "spo2" },
  { title: "Kelembapan", unit: "%", dataKey: "kelembapan_inkubator", thresholdKey: "kelembapan_inkubator" },
];

function clockLabel(iso: string) {
  return new Date(iso).toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

type Row = SensorReading & { t: string };

/**
 * One y-domain per scale group, covering every panel in it plus its threshold
 * band, with a little headroom so lines never touch the frame.
 */
function sharedDomains(
  rows: Row[],
  bounds: ThresholdMetric[],
): Record<string, [number, number]> {
  const out: Record<string, [number, number]> = {};
  const groups = new Set(PANELS.map((p) => p.scaleGroup).filter(Boolean) as string[]);

  for (const g of groups) {
    const vals: number[] = [];
    for (const p of PANELS.filter((x) => x.scaleGroup === g)) {
      for (const r of rows) {
        const v = r[p.dataKey];
        if (typeof v === "number") vals.push(v);
      }
      const b = bounds.find((x) => x.key === p.thresholdKey);
      if (b?.min != null) vals.push(b.min);
      if (b?.max != null) vals.push(b.max);
    }
    if (vals.length === 0) continue;
    const lo = Math.min(...vals);
    const hi = Math.max(...vals);
    const pad = Math.max((hi - lo) * 0.12, 0.5);
    out[g] = [Math.floor(lo - pad), Math.ceil(hi + pad)];
  }
  return out;
}

export function SensorChartCard({ incubatorId }: { incubatorId: string }) {
  const readings = useSensorReadings(incubatorId);

  // Bands come from the per-incubator threshold settings that already ship, so
  // they follow any admin override for free.
  const thresholds = useQuery({
    queryKey: ["thresholds", incubatorId],
    queryFn: async () =>
      (await api.get<IncubatorThresholds>(`/incubators/${incubatorId}/thresholds`))
        .data,
  });

  if (readings.isLoading) {
    return (
      <Card className="p-5">
        <SectionTitle>Tren Sensor</SectionTitle>
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      </Card>
    );
  }

  const rows = readings.data ?? [];

  if (rows.length === 0) {
    return (
      <Card className="p-5">
        <SectionTitle>Tren Sensor</SectionTitle>
        <p className="mt-2 text-sm text-muted">
          Belum ada data sensor untuk inkubator ini. Grafik akan muncul otomatis
          setelah perangkat mulai mengirim.
        </p>
      </Card>
    );
  }

  const data: Row[] = rows.map((r) => ({ ...r, t: clockLabel(r.recorded_at) }));
  const bounds = thresholds.data?.metrics ?? [];
  const domains = sharedDomains(data, bounds);

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <SectionTitle>Tren Sensor</SectionTitle>
        <span className="flex items-center gap-1.5 text-xs text-muted">
          <span
            aria-hidden
            className={`h-1.5 w-1.5 rounded-full ${
              readings.streaming ? "bg-ok" : "bg-kosong"
            }`}
          />
          {readings.streaming ? "Langsung" : "Berkala"} · {rows.length} pembacaan
        </span>
      </div>

      {/* One column on purpose: full width makes the axis numbers and the
          shape of the trend legible, which 3-up thumbnails did not. */}
      <div className="mt-4 flex flex-col gap-5">
        {PANELS.map((p) => (
          <SensorPanel
            key={p.title}
            panel={p}
            data={data}
            bounds={bounds}
            domain={p.scaleGroup ? domains[p.scaleGroup] : undefined}
          />
        ))}
      </div>

      <p className="mt-4 border-t border-line pt-3 text-[11.5px] leading-relaxed text-muted">
        Garis terputus berarti sensor tidak mengirim nilai pada saat itu —
        misalnya probe lepas dari bayi. Itu <strong>bukan</strong> nilai nol.
        Suhu bayi dan suhu inkubator memakai skala yang sama agar bisa
        dibandingkan langsung.
      </p>
    </Card>
  );
}

function SensorPanel({
  panel,
  data,
  bounds,
  domain,
}: {
  panel: Panel;
  data: Row[];
  bounds: ThresholdMetric[];
  domain?: [number, number];
}) {
  const band = bounds.find((b) => b.key === panel.thresholdKey);
  const hasBand = band && (band.min != null || band.max != null);
  const hasAny = data.some((d) => d[panel.dataKey] != null);

  // Latest actual value, shown beside the title so the current reading is
  // legible without hovering — the chart answers "trend", this answers "now".
  const latest = [...data].reverse().find((d) => d[panel.dataKey] != null);
  const latestValue = latest ? (latest[panel.dataKey] as number) : null;

  return (
    // min-w-0 is load-bearing: a grid item defaults to min-width:auto, so
    // ResponsiveContainer never shrinks below the width it first measured and
    // the whole page gains a horizontal scrollbar on narrow screens.
    <div className="min-w-0">
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <h4 className="truncate text-[13.5px] font-bold text-ink">
          {panel.title}{" "}
          <span className="font-medium text-muted">({panel.unit})</span>
        </h4>
        <span className="shrink-0 text-[15px] font-extrabold tabular-nums text-ink">
          {latestValue != null ? (
            <>
              {latestValue}
              <span className="ml-1 text-[12px] font-semibold text-muted">
                {panel.unit}
              </span>
            </>
          ) : (
            <span className="text-[13px] font-bold text-muted">—</span>
          )}
        </span>
      </div>

      {hasAny ? (
        <ResponsiveContainer width="100%" height={190}>
          <LineChart data={data} margin={{ top: 6, right: 12, bottom: 0, left: -12 }}>
            <CartesianGrid stroke="#eef2f7" vertical={false} />
            {hasBand && (
              <ReferenceArea
                y1={band!.min ?? undefined}
                y2={band!.max ?? undefined}
                fill="#94a3b8"
                fillOpacity={0.08}
                ifOverflow="extendDomain"
              />
            )}
            <XAxis
              dataKey="t"
              tick={{ fontSize: 10, fill: "#94a3b8" }}
              tickLine={false}
              axisLine={false}
              minTickGap={70}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#94a3b8" }}
              tickLine={false}
              axisLine={false}
              width={42}
              domain={domain ?? ["auto", "auto"]}
              allowDecimals
            />
            <Tooltip
              contentStyle={{
                borderRadius: 12,
                border: "1px solid #e9eef5",
                fontSize: 12,
              }}
              labelStyle={{ color: "#64748b", fontSize: 11 }}
              formatter={(v) => [`${v ?? "—"} ${panel.unit}`, panel.title]}
            />
            <Line
              type="monotone"
              dataKey={panel.dataKey as string}
              name={panel.title}
              stroke={LINE}
              strokeWidth={2}
              // A line needs two points. This pulse-ox drops in and out, so a
              // lone reading between nulls is common — and with dot={false} it
              // would draw a zero-length path and vanish entirely. Mark only
              // those isolated points, so nothing recorded goes unseen without
              // peppering 120 dots over a continuous trace.
              dot={(props) => {
                const { cx, cy, index, key } = props as {
                  cx?: number; cy?: number; index: number; key?: string;
                };
                const has = (i: number) =>
                  i >= 0 && i < data.length && data[i][panel.dataKey] != null;
                const isolated = !has(index - 1) && !has(index + 1);
                if (!isolated || cx == null || cy == null) return <g key={key} />;
                return <circle key={key} cx={cx} cy={cy} r={2.5} fill={LINE} />;
              }}
              isAnimationActive={false}
              // No connectNulls: a gap is the honest rendering of "no reading".
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div className="flex h-[190px] items-center justify-center rounded-xl bg-surface">
          <p className="px-4 text-center text-[12px] text-muted">
            {/* Title verbatim, not lowercased — toLowerCase mangles "SpO₂". */}
            Sensor belum mengirim nilai untuk {panel.title}.
          </p>
        </div>
      )}
    </div>
  );
}
