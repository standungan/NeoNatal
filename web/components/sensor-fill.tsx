"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { SensorReading } from "@/lib/types";

/**
 * Offers the latest sensor reading to the vitals form.
 *
 * Deliberately an ACTION, not a silent pre-fill. A charted observation is a
 * nurse's statement about the baby, and fields populated on page load can be
 * submitted without ever being read — so the values are shown first, their age
 * is stated, and filling them in takes a click.
 *
 * Respiratory rate is never offered: no sensor produces it, so it stays typed.
 */

/** Beyond this, a reading is history rather than a description of "now". */
const STALE_AFTER_MS = 120_000;

export type SensorFillValues = {
  suhuBayi: string;
  suhuInkubator: string;
  kelembapan: string;
  heartRate: string;
  spo2: string;
};

function ageLabel(ms: number): string {
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s} detik lalu`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m} menit lalu`;
  return `${Math.round(m / 60)} jam lalu`;
}

const fmt = (v: number | null) => (v == null ? "" : String(v));

export function SensorFillBanner({
  babyId,
  onFill,
}: {
  babyId: string;
  onFill: (v: SensorFillValues) => void;
}) {
  const q = useQuery({
    queryKey: ["latest-reading", babyId],
    queryFn: async () =>
      (await api.get<SensorReading | null>(`/babies/${babyId}/latest-reading`))
        .data,
    refetchInterval: 10_000,
  });

  // Re-render on a timer so the stated age decays while the form sits open —
  // otherwise "3 detik lalu" would still claim that ten minutes later.
  const [, tick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 5_000);
    return () => clearInterval(id);
  }, []);

  const r = q.data;
  // No device, no assignment, or nothing recorded yet — all ordinary. Say
  // nothing rather than explaining an absence the nurse did not ask about.
  if (!r) return null;

  const age = Date.now() - new Date(r.recorded_at).getTime();
  const stale = age > STALE_AFTER_MS;

  const parts = [
    r.suhu_bayi != null && `Suhu ${r.suhu_bayi}°C`,
    r.heart_rate != null && `HR ${r.heart_rate}`,
    r.spo2 != null && `SpO₂ ${r.spo2}%`,
    r.kelembapan_inkubator != null && `RH ${r.kelembapan_inkubator}%`,
  ].filter(Boolean) as string[];

  // Every metric null means the device is alive but nothing is on the baby;
  // offering to fill blank fields would be pure noise.
  if (parts.length === 0) return null;

  return (
    <div
      className={
        "rounded-xl border p-3 " +
        (stale ? "border-warn/40 bg-warn/5" : "border-primary/30 bg-primary/5")
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="min-w-0">
          <p className="text-[13px] font-bold text-ink">
            Pembacaan sensor terakhir
            <span
              className={
                "ml-2 font-semibold " + (stale ? "text-warn" : "text-muted")
              }
            >
              {ageLabel(age)}
            </span>
          </p>
          <p className="mt-0.5 text-[12.5px] text-muted">{parts.join(" · ")}</p>
        </div>

        <button
          type="button"
          onClick={() =>
            onFill({
              suhuBayi: fmt(r.suhu_bayi),
              suhuInkubator: fmt(r.suhu_inkubator),
              kelembapan: fmt(r.kelembapan_inkubator),
              heartRate: fmt(r.heart_rate),
              spo2: fmt(r.spo2),
            })
          }
          className="shrink-0 rounded-lg border border-line bg-card px-3 py-1 text-[12.5px] font-bold text-ink hover:bg-surface"
        >
          Isi dari sensor
        </button>
      </div>

      {stale && (
        <p className="mt-2 text-[11.5px] leading-relaxed text-muted">
          Pembacaan ini sudah lama. Periksa alat sebelum memakainya sebagai
          catatan observasi saat ini.
        </p>
      )}
      <p className="mt-1.5 text-[11.5px] leading-relaxed text-muted">
        Nilai terisi otomatis tetap bisa Anda ubah — yang tersimpan adalah
        observasi Anda, bukan pembacaan alat.
      </p>
    </div>
  );
}
