type Tone = "ok" | "warn" | "off";

const toneStyles: Record<Tone, string> = {
  ok: "border-emerald-500/40 bg-emerald-500/10",
  warn: "border-red-500/50 bg-red-500/10",
  off: "border-slate-700 bg-slate-800/40",
};

const valueColor: Record<Tone, string> = {
  ok: "text-emerald-300",
  warn: "text-red-300",
  off: "text-slate-200",
};

export function WidgetCard({
  title,
  value,
  unit,
  tone = "off",
  sub,
}: {
  title: string;
  value: string;
  unit?: string;
  tone?: Tone;
  sub?: string;
}) {
  return (
    <div className={`rounded-2xl border p-4 ${toneStyles[tone]}`}>
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">{title}</div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className={`text-4xl font-semibold tabular-nums ${valueColor[tone]}`}>{value}</span>
        {unit && <span className="text-sm text-slate-400">{unit}</span>}
      </div>
      {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
    </div>
  );
}
