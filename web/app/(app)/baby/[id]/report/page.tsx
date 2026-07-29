"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceArea,
  ResponsiveContainer,
} from "recharts";
import { api } from "@/lib/api";
import type { BabyReport, MonitoringRecord, ObservationRecord, AksiRecord } from "@/lib/types";
import { Card, PageState, BackLink, SectionTitle } from "@/components/ui";
import { formatDateTime, genderLabel } from "@/lib/format";
import { ObservationSummaryCard } from "@/components/observation";
import { InvolvementSummaryCard } from "@/components/involvement";
import { AksiSummaryCard } from "@/components/aksi";
import { RegistrationCard, BabyIdentityCard, MaternalRecordCard } from "@/components/maternal";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["report", id],
    queryFn: async () =>
      (await api.get<BabyReport>(`/babies/${id}/report`)).data,
  });

  const observationQ = useQuery({
    queryKey: ["observation", id],
    queryFn: async () =>
      (await api.get<ObservationRecord[]>(`/babies/${id}/observation?limit=1`)).data,
  });
  const latestObservation = observationQ.data?.[0];

  const aksiQ = useQuery({
    queryKey: ["aksi", id],
    queryFn: async () =>
      (await api.get<AksiRecord[]>(`/babies/${id}/aksi?limit=1`)).data,
  });
  const latestAksi = aksiQ.data?.[0];

  return (
    <div>
      <BackLink href="/dashboard" label="Kembali ke Dashboard" />
      <h1 className="mb-4 mt-3 text-xl font-extrabold text-ink">
        Laporan &amp; Riwayat Bayi
      </h1>

      <PageState loading={isLoading} error={error} onRetry={() => refetch()}>
        {data && (
          <div className="flex flex-col gap-4">
            <Card className="p-5">
              <div className="flex items-center gap-3.5">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-xl">
                  👶
                </div>
                <div className="flex-1">
                  <p className="text-base font-extrabold text-ink">
                    {data.baby.baby_name}
                  </p>
                  <p className="text-xs text-muted">
                    Hari ke-{data.baby.age_in_days} ·{" "}
                    {data.baby.birth_weight != null
                      ? `${data.baby.birth_weight} gram`
                      : "-"}{" "}
                    · {genderLabel(data.baby.gender)}
                  </p>
                </div>
                <a
                  href={`/api/v1/babies/${id}/report/pdf`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary-dark"
                >
                  📄 Export PDF
                </a>
              </div>
            </Card>

            {data.baby.current_assignment && (
              <RegistrationCard assignment={data.baby.current_assignment} />
            )}

            <BabyIdentityCard baby={data.baby} />

            {data.baby.maternal && (
              <MaternalRecordCard maternal={data.baby.maternal} parent={data.baby.parent} />
            )}

            {latestObservation && <ObservationSummaryCard record={latestObservation} />}

            {data.baby.latest_vitals && (
              <LatestVitalsCard vitals={data.baby.latest_vitals} />
            )}

            <InvolvementStatsCard summary={data.involvement_summary} />

            {data.involvement_history.length > 0 && (
              <InvolvementSummaryCard record={data.involvement_history[0]} />
            )}

            {latestAksi && <AksiSummaryCard record={latestAksi} />}

            <HistoryCard records={data.monitoring_history} />

            <Card className="p-5">
              <SectionTitle>Grafik Tren Vital</SectionTitle>
              <div className="mt-4 flex flex-col gap-6">
                <VitalChart
                  title="Suhu Bayi (°C)"
                  color="#f59e0b"
                  records={data.monitoring_history}
                  field="suhu_bayi"
                  domain={[34, 40]}
                  normal={[36, 37.5]}
                />
                <VitalChart
                  title="Heart Rate (bpm)"
                  color="#ef4444"
                  records={data.monitoring_history}
                  field="heart_rate"
                  domain={[70, 200]}
                  normal={[100, 160]}
                />
                <VitalChart
                  title="SpO₂ (%)"
                  color="#2563eb"
                  records={data.monitoring_history}
                  field="spo2"
                  domain={[80, 100]}
                  normal={[93, 100]}
                />
              </div>
            </Card>
          </div>
        )}
      </PageState>
    </div>
  );
}

function LatestVitalsCard({ vitals }: { vitals: MonitoringRecord }) {
  const warn = vitals.vital_status === "warning";
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <SectionTitle>Kondisi Terkini</SectionTitle>
        <span
          className={`inline-flex items-center gap-1.5 text-[13px] font-semibold ${
            warn ? "text-warn" : "text-ok"
          }`}
        >
          <span
            className={`h-2.5 w-2.5 rounded-full ${warn ? "bg-warn" : "bg-ok"}`}
          />
          {warn ? "Perhatian" : "Normal"}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
        <VitalTile label="Suhu Bayi" value={vitals.suhu_bayi != null ? `${vitals.suhu_bayi} °C` : "-"} />
        <VitalTile label="Suhu Inkubator" value={vitals.suhu_inkubator != null ? `${vitals.suhu_inkubator} °C` : "-"} />
        <VitalTile label="Kelembapan Inkubator" value={vitals.kelembapan_inkubator != null ? `${vitals.kelembapan_inkubator} %` : "-"} />
        <VitalTile label="Heart Rate" value={vitals.heart_rate != null ? `${vitals.heart_rate} bpm` : "-"} />
        <VitalTile label="Respiratory Rate" value={vitals.respiratory_rate != null ? `${vitals.respiratory_rate} /mnt` : "-"} />
        <VitalTile label="SpO₂" value={vitals.spo2 != null ? `${vitals.spo2} %` : "-"} />
        <VitalTile label="Nyeri (NIPS)" value={vitals.pain_score != null ? `${vitals.pain_score} / 7` : "-"} />
        <VitalTile label="Ekspresi" value={vitals.expression_score != null ? `${vitals.expression_score} / 5` : "-"} />
        <VitalTile label="Gerakan" value={vitals.movement_score != null ? `${vitals.movement_score} / 5` : "-"} />
        <VitalTile label="Durasi Tidur" value={vitals.sleep_duration_min != null ? `${vitals.sleep_duration_min} mnt` : "-"} />
        <VitalTile label="Kualitas Tidur" value={vitals.sleep_quality != null ? `${vitals.sleep_quality} / 5` : "-"} />
        <VitalTile label="Episode Gelisah" value={vitals.agitation_episodes != null ? `${vitals.agitation_episodes}` : "-"} />
      </div>
    </Card>
  );
}

function VitalTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-line bg-[#f8fafc] px-3.5 py-2.5 text-center">
      <div className="text-[11px] text-muted">{label}</div>
      <div className="mt-0.5 text-[13px] font-extrabold text-ink">{value}</div>
    </div>
  );
}

function InvolvementStatsCard({
  summary,
}: {
  summary: BabyReport["involvement_summary"];
}) {
  return (
    <Card className="p-5">
      <SectionTitle>Keterlibatan Orang Tua</SectionTitle>
      <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <div>
          <span className="text-muted">Total sesi: </span>
          <span className="font-bold text-ink">{summary.total_sessions}</span>
        </div>
        <div>
          <span className="text-muted">Rata-rata: </span>
          <span className="font-bold text-ink">
            {summary.avg_percentage != null ? `${summary.avg_percentage.toFixed(1)}%` : "-"}
          </span>
        </div>
        {summary.latest_category && (
          <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            Terakhir: {summary.latest_category}
          </span>
        )}
      </div>
    </Card>
  );
}

function VitalChart({
  title,
  color,
  records,
  field,
  domain,
  normal,
}: {
  title: string;
  color: string;
  records: MonitoringRecord[];
  field: "suhu_bayi" | "heart_rate" | "spo2";
  domain: [number, number];
  normal: [number, number];
}) {
  const data = [...records]
    .reverse()
    .map((r, i) => ({ i, value: r[field] != null ? Number(r[field]) : null }));

  const hasEnough = data.filter((d) => d.value != null).length >= 2;

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
        <span className="text-[13px] font-semibold" style={{ color }}>
          {title}
        </span>
      </div>
      {hasEnough ? (
        <ResponsiveContainer width="100%" height={170}>
          <LineChart data={data} margin={{ top: 6, right: 12, bottom: 0, left: -10 }}>
            <CartesianGrid stroke="#eef2f7" vertical={false} />
            <ReferenceArea
              y1={normal[0]}
              y2={normal[1]}
              fill="#10b981"
              fillOpacity={0.07}
            />
            <XAxis dataKey="i" hide />
            <YAxis
              domain={domain}
              tick={{ fontSize: 10, fill: "#94a3b8" }}
              width={34}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 12,
                border: "1px solid #e9eef5",
                fontSize: 12,
              }}
              labelFormatter={() => ""}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2.5}
              dot={{ r: 3, fill: color }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p className="py-8 text-center text-[13px] text-muted">
          Butuh minimal 2 data untuk menampilkan grafik
        </p>
      )}
    </div>
  );
}

function HistoryCard({ records }: { records: MonitoringRecord[] }) {
  return (
    <Card className="p-5">
      <SectionTitle>Riwayat Monitoring ({records.length} entri)</SectionTitle>
      {records.length === 0 ? (
        <p className="mt-3 text-sm text-muted">Belum ada data monitoring.</p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead>
              <tr className="text-muted">
                <th className="py-2 font-semibold">Waktu</th>
                <th className="py-2 font-semibold">Suhu</th>
                <th className="py-2 font-semibold">HR</th>
                <th className="py-2 font-semibold">RR</th>
                <th className="py-2 font-semibold">SpO₂</th>
                <th className="py-2 font-semibold">Nyeri</th>
                <th className="py-2 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {records.slice(0, 12).map((r) => (
                <tr key={r.monitoring_id} className="border-t border-line">
                  <td className="py-2 text-muted">
                    {formatDateTime(r.observation_time)}
                  </td>
                  <td className="py-2">{r.suhu_bayi ?? "-"}°C</td>
                  <td className="py-2">{r.heart_rate ?? "-"} bpm</td>
                  <td className="py-2">{r.respiratory_rate ?? "-"} /mnt</td>
                  <td className="py-2">{r.spo2 ?? "-"}%</td>
                  <td className="py-2">{r.pain_score ?? "-"}</td>
                  <td className="py-2">
                    <span
                      className={`inline-block h-2.5 w-2.5 rounded-full ${
                        r.vital_status === "warning" ? "bg-warn" : "bg-ok"
                      }`}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
