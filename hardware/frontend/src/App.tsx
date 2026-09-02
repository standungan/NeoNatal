import { useState } from "react";
import { useSensorData } from "./hooks/useSensorData";
import { WidgetCard } from "./components/WidgetCard";
import { VitalsChart } from "./components/VitalsChart";
import { EnvChart } from "./components/EnvChart";

type Tone = "ok" | "warn" | "off";

const fmt = (v: number | null | undefined, digits = 1) =>
  v == null ? "--" : v.toFixed(digits);

// HR normal 60-100 bpm; 0/absen = tidak ada jari
function hrTone(hr?: number): Tone {
  if (!hr || hr <= 0) return "off";
  return hr >= 60 && hr <= 100 ? "ok" : "warn";
}

// SpO2 < 95% = waspada
function spo2Tone(spo2?: number): Tone {
  if (!spo2 || spo2 <= 0) return "off";
  return spo2 < 95 ? "warn" : "ok";
}

export default function App() {
  const [incubatorId, setIncubatorId] = useState("INC-01");
  const { latest, history, online } = useSensorData(incubatorId);
  const s = latest?.sensors;

  const hr = s?.heart_rate;
  const spo2 = s?.spo2;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-4 py-6">
        {/* Header */}
        <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">Baby Monitor</h1>
            <p className="text-sm text-slate-400">
              Incubator <span className="font-mono text-slate-300">{incubatorId}</span>
              {latest?.baby_id && (
                <>
                  {" · "}Baby <span className="font-mono text-slate-300">{latest.baby_id}</span>
                </>
              )}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              value={incubatorId}
              onChange={(e) => setIncubatorId(e.target.value.trim())}
              className="w-32 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm outline-none focus:border-slate-500"
              placeholder="incubator_id"
              aria-label="Incubator ID"
            />
            <span
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm ${
                online
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                  : "border-red-500/40 bg-red-500/10 text-red-300"
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${online ? "bg-emerald-400" : "bg-red-400"}`} />
              {online ? "Online" : "Offline"}
            </span>
          </div>
        </header>

        {/* Widget cards */}
        <section className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <WidgetCard
            title="Heart Rate"
            value={hr && hr > 0 ? String(Math.round(hr)) : "--"}
            unit="bpm"
            tone={hrTone(hr)}
            sub="normal 60–100"
          />
          <WidgetCard
            title="SpO2"
            value={spo2 && spo2 > 0 ? String(Math.round(spo2)) : "--"}
            unit="%"
            tone={spo2Tone(spo2)}
            sub="normal ≥ 95"
          />
          <WidgetCard title="Suhu Probe" value={fmt(s?.ds18b20_temp)} unit="°C" sub="DS18B20" />
          <WidgetCard title="Suhu Ruang" value={fmt(s?.dht22_temp)} unit="°C" sub="DHT22" />
          <WidgetCard title="Kelembaban" value={fmt(s?.dht22_humidity, 0)} unit="%" sub="DHT22" />
        </section>

        {/* Grafik */}
        <section className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
          <VitalsChart data={history} />
          <EnvChart data={history} />
        </section>
      </div>
    </div>
  );
}
