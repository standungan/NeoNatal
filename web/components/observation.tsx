"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";
import type { ObservationPillarScore } from "@/lib/types";

export const PILLAR_SHORT: Record<string, string> = {
  tidur: "Tidur",
  nyeri: "Nyeri",
  posisi: "Posisi",
  kulit: "Kulit",
  nutrisi: "Nutrisi",
  keluarga: "Keluarga",
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
