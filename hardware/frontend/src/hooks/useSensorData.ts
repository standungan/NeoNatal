import { useEffect, useRef, useState } from "react";
import { io, type Socket } from "socket.io-client";
import type { Reading, ChartPoint } from "../types";

// Default "" = origin yang sama dgn halaman ini (prod: di-serve backend; dev:
// via proxy Vite). Override VITE_BACKEND_URL hanya kalau backend beda host/port.
const BACKEND = import.meta.env.VITE_BACKEND_URL || "";
const MAX_POINTS = 60; // simpan N titik terakhir untuk grafik realtime
const OFFLINE_MS = 12000; // device dianggap offline jika tak ada data > ini

// ponytail: HR/SpO2 = 0 artinya "tidak ada jari" -> jadikan undefined biar
// grafik menggambar putus, bukan garis jatuh ke nol.
const orUndef = (v?: number) => (v && v > 0 ? v : undefined);
const numOrUndef = (v?: number | null) => (v == null ? undefined : v);

export function useSensorData(incubatorId: string) {
  const [latest, setLatest] = useState<Reading | null>(null);
  const [history, setHistory] = useState<ChartPoint[]>([]);
  const [online, setOnline] = useState(false);
  const lastSeen = useRef(0);

  useEffect(() => {
    setLatest(null);
    setHistory([]);
    setOnline(false);
    lastSeen.current = 0;

    const ingest = (r: Reading) => {
      lastSeen.current = Date.now();
      setOnline(true);
      setLatest(r);
      const s = r.sensors;
      const point: ChartPoint = {
        t: new Date(r.created_at).toLocaleTimeString(),
        heart_rate: orUndef(s.heart_rate),
        spo2: orUndef(s.spo2),
        ds18b20_temp: numOrUndef(s.ds18b20_temp),
        dht22_temp: numOrUndef(s.dht22_temp),
        dht22_humidity: numOrUndef(s.dht22_humidity),
      };
      setHistory((prev) => [...prev, point].slice(-MAX_POINTS));
    };

    // Load awal: reading terakhir dari DB
    fetch(`${BACKEND}/api/sensors/latest?incubator_id=${encodeURIComponent(incubatorId)}`)
      .then((res) => res.json())
      .then((r: Reading | null) => r && ingest(r))
      .catch(() => {});

    const socket: Socket = io(BACKEND || undefined);
    const join = () => socket.emit("join", incubatorId);
    socket.on("connect", join); // re-join saat (re)connect
    socket.on("reading", ingest);

    const timer = setInterval(() => {
      setOnline(lastSeen.current > 0 && Date.now() - lastSeen.current < OFFLINE_MS);
    }, 2000);

    return () => {
      socket.disconnect();
      clearInterval(timer);
    };
  }, [incubatorId]);

  return { latest, history, online };
}
