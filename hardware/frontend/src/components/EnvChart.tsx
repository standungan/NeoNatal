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

export function EnvChart({ data }: { data: ChartPoint[] }) {
  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-800/40 p-4">
      <h2 className="mb-3 text-sm font-medium text-slate-300">Suhu &amp; Kelembaban</h2>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 5, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="t" tick={{ fontSize: 11, fill: "#94a3b8" }} minTickGap={40} />
          <YAxis yAxisId="temp" domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#fbbf24" }} width={34} />
          <YAxis
            yAxisId="hum"
            orientation="right"
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: "#34d399" }}
            width={34}
          />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            yAxisId="temp"
            type="monotone"
            dataKey="ds18b20_temp"
            name="Probe DS18B20 (°C)"
            stroke="#fb923c"
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            yAxisId="temp"
            type="monotone"
            dataKey="dht22_temp"
            name="Ruang DHT22 (°C)"
            stroke="#fbbf24"
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            yAxisId="hum"
            type="monotone"
            dataKey="dht22_humidity"
            name="Humidity (%)"
            stroke="#34d399"
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
