"use client";

/**
 * Tiny skin-temperature trace for a dashboard card.
 *
 * Hand-rolled SVG rather than a chart library: at 20px tall there are no axes,
 * ticks or tooltips to earn the dependency, and Recharts' ResponsiveContainer
 * inside a grid needs `min-w-0` care that a plain <svg> simply does not.
 *
 * A null BREAKS the trace, exactly as on the full chart — the sensor reporting
 * nothing is not the same as a value, and a continuous line across a gap would
 * invent readings that were never taken.
 */
export function Sparkline({
  values,
  width = 96,
  height = 22,
  className = "",
}: {
  values: (number | null)[];
  width?: number;
  height?: number;
  className?: string;
}) {
  const present = values.filter((v): v is number => v != null);
  // Two points make a line; one makes a dot, and none makes nothing. Rendering
  // an empty frame would imply "no change" rather than "no data".
  if (present.length < 2) return null;

  const lo = Math.min(...present);
  const hi = Math.max(...present);
  const span = hi - lo || 1;
  const pad = 2;
  const usableH = height - pad * 2;

  const x = (i: number) =>
    values.length < 2 ? 0 : (i / (values.length - 1)) * width;
  const y = (v: number) => pad + (1 - (v - lo) / span) * usableH;

  // Split into contiguous runs so gaps stay gaps.
  const runs: string[] = [];
  let current: string[] = [];
  values.forEach((v, i) => {
    if (v == null) {
      if (current.length > 1) runs.push(current.join(" "));
      current = [];
    } else {
      current.push(`${x(i).toFixed(1)},${y(v).toFixed(1)}`);
    }
  });
  if (current.length > 1) runs.push(current.join(" "));

  const lastIdx = values.map((v, i) => (v == null ? -1 : i)).filter((i) => i >= 0).pop()!;
  const lastVal = values[lastIdx] as number;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      // Decorative: the numeric values sit beside it in the card, so a screen
      // reader gains nothing from the path and would only add noise.
      aria-hidden
      focusable="false"
    >
      {runs.map((pts, i) => (
        <polyline
          key={i}
          points={pts}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ))}
      <circle cx={x(lastIdx)} cy={y(lastVal)} r={1.8} fill="currentColor" />
    </svg>
  );
}
