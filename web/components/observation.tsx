"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";
import type { ObservationPillarScore, ObservationRecord } from "@/lib/types";
import { Card, SectionTitle } from "@/components/ui";
import { formatDateTime } from "@/lib/format";

export const PILLAR_SHORT: Record<string, string> = {
  tidur: "Tidur",
  nyeri: "Nyeri",
  posisi: "Posisi",
  kulit: "Kulit",
  nutrisi: "Nutrisi",
  lingkungan: "Lingkungan",
  kolaborasi: "Kolaborasi",
};

/** Tailwind text-color class for a category label. */
export function categoryColor(cat: string | null | undefined): string {
  switch (cat) {
    case "Sangat Baik":
      return "text-ok";
    case "Baik":
      return "text-primary";
    case "Cukup":
      return "text-accent";
    case "Kurang":
      return "text-warn";
    default:
      return "text-danger"; // Sangat Kurang
  }
}

export function categoryFor(percentage: number): string {
  if (percentage >= 85) return "Sangat Baik";
  if (percentage >= 70) return "Baik";
  if (percentage >= 55) return "Cukup";
  if (percentage >= 40) return "Kurang";
  return "Sangat Kurang";
}

export function ObservationRadar({
  pillars,
  height = 280,
}: {
  pillars: ObservationPillarScore[];
  height?: number;
}) {
  const data = pillars.map((p) => ({
    pillar: PILLAR_SHORT[p.key] ?? p.label,
    value: p.percentage,
  }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke="#e9eef5" />
        <PolarAngleAxis dataKey="pillar" tick={{ fontSize: 11, fill: "#64748b" }} />
        <PolarRadiusAxis domain={[0, 100]} angle={90} tick={{ fontSize: 9, fill: "#94a3b8" }} />
        <Radar dataKey="value" stroke="#2563eb" fill="#2563eb" fillOpacity={0.25} strokeWidth={2} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

/** Latest-observation summary: score + category + per-pillar bars + alarms + radar.
 *  Shared by the report page and the incubator detail page. */
export function ObservationSummaryCard({
  record,
  title = "Monitoring Bayi",
}: {
  record: ObservationRecord;
  title?: string;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <SectionTitle>{title}</SectionTitle>
        <span className="text-xs text-muted">{formatDateTime(record.observation_time)}</span>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <div className="flex items-end gap-3">
            <span className={`text-5xl font-extrabold ${categoryColor(record.category)}`}>
              {record.percentage}%
            </span>
            <span className={`mb-1 rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold ${categoryColor(record.category)}`}>
              {record.category ?? "-"}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted">
            {record.total_score} / {record.max_total} poin
          </p>
          <div className="mt-3 flex flex-col gap-1.5">
            {record.pillars.map((p) => (
              <div key={p.key} className="flex items-center gap-3">
                <span className="w-28 shrink-0 text-[12.5px] text-ink">{PILLAR_SHORT[p.key] ?? p.label}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-[#eef2f7]">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${p.percentage}%` }} />
                </div>
                <span className="w-10 shrink-0 text-right text-[12px] font-bold text-ink">{p.percentage}%</span>
              </div>
            ))}
          </div>
          {record.alarms.length > 0 && (
            <div className="mt-3 rounded-xl border border-danger/30 bg-danger/5 p-3">
              <p className="text-[13px] font-bold text-danger">⚠ {record.alarms.length} item perlu perhatian</p>
              <ul className="mt-1 max-h-24 overflow-auto text-[12px] text-ink">
                {record.alarms.slice(0, 6).map((a) => (
                  <li key={a.item_code} className="truncate">• {a.text} <span className="text-muted">(skor {a.score})</span></li>
                ))}
                {record.alarms.length > 6 && <li className="text-muted">…dan {record.alarms.length - 6} lainnya</li>}
              </ul>
            </div>
          )}
        </div>
        <ObservationRadar pillars={record.pillars} />
      </div>
    </Card>
  );
}
