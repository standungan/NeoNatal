import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartPoint } from "../types";

const tooltipStyle = {
  background: "#0f172a",
  border: "1px solid #334155",
  borderRadius: 8,
  color: "#e2e8f0",
};

export function VitalsChart({ data }: { data: ChartPoint[] }) {
  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-800/40 p-4">
      <h2 className="mb-3 text-sm font-medium text-slate-300">Heart Rate &amp; SpO2</h2>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 5, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="t" tick={{ fontSize: 11, fill: "#94a3b8" }} minTickGap={40} />
          <YAxis yAxisId="hr" domain={[40, 180]} tick={{ fontSize: 11, fill: "#f87171" }} width={34} />
          <YAxis
            yAxisId="spo2"
            orientation="right"
            domain={[80, 100]}
            tick={{ fontSize: 11, fill: "#38bdf8" }}
            width={34}
          />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            yAxisId="hr"
            type="monotone"
            dataKey="heart_rate"
            name="HR (bpm)"
            stroke="#f87171"
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            yAxisId="spo2"
            type="monotone"
            dataKey="spo2"
            name="SpO2 (%)"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
