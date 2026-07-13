"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";
import type { AksiRecord } from "@/lib/types";
import { Card, SectionTitle } from "@/components/ui";
import { formatDateTime } from "@/lib/format";

/** Short axis labels for the 6 Kolaborasi Interprofesional items (keyed by item_code). */
export const ITEM_SHORT: Record<string, string> = {
  kolaborasi_1: "CPPT",
  kolaborasi_2: "SBAR",
  kolaborasi_3: "Instruksi",
  kolaborasi_4: "Lapor",
  kolaborasi_5: "Kolaborasi",
  kolaborasi_6: "Dokumentasi",
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

export type RadarItem = { item_code: string; text: string; score: number };

/** Spider/radar chart of the 6 "Kolaborasi Interprofesional" items (0–3 scale).
 *  Shared by the Aksi entry form (live) and the report page (latest record). */
export function AksiRadar({ items, height = 280 }: { items: RadarItem[]; height?: number }) {
  const data = items.map((it) => ({ item: ITEM_SHORT[it.item_code] ?? it.text, value: it.score }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke="#e9eef5" />
        <PolarAngleAxis dataKey="item" tick={{ fontSize: 11, fill: "#64748b" }} />
        <PolarRadiusAxis domain={[0, 3]} tickCount={4} angle={90} tick={{ fontSize: 9, fill: "#94a3b8" }} />
        <Radar dataKey="value" stroke="#2563eb" fill="#2563eb" fillOpacity={0.25} strokeWidth={2} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

/** Latest-aksi summary: score + category + per-item bars + alarms + radar.
 *  Used on the report page. */
export function AksiSummaryCard({
  record,
  title = "Kolaborasi Interprofesional",
}: {
  record: AksiRecord;
  title?: string;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <SectionTitle>{title}</SectionTitle>
        <span className="text-xs text-muted">{formatDateTime(record.observation_time)}</span>
      </div>
      <p className="mt-0.5 text-[11px] text-muted">Menu Aksi — Pilar 8</p>
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
            {record.items.map((it) => (
              <div key={it.item_code} className="flex items-center gap-3">
                <span className="w-36 shrink-0 text-[12.5px] text-ink">{ITEM_SHORT[it.item_code] ?? it.text}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-[#eef2f7]">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${it.percentage}%` }} />
                </div>
                <span className="w-8 shrink-0 text-right text-[12px] font-bold text-ink">{it.score}/{it.max}</span>
              </div>
            ))}
          </div>
          {record.alarms.length > 0 && (
            <div className="mt-3 rounded-xl border border-danger/30 bg-danger/5 p-3">
              <p className="text-[13px] font-bold text-danger">⚠ {record.alarms.length} item perlu perhatian</p>
              <ul className="mt-1 text-[12px] text-ink">
                {record.alarms.map((a) => (
                  <li key={a.item_code} className="truncate">• {a.text} <span className="text-muted">(skor {a.score})</span></li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <AksiRadar items={record.items} />
      </div>
    </Card>
  );
}
