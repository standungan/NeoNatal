"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { DashboardResponse, IncubatorDashboardItem } from "@/lib/types";
import { Card, StatCard, StatusBadge, PageState } from "@/components/ui";
import { useAuth } from "@/components/providers";
import { canWrite } from "@/lib/format";

export default function DashboardPage() {
  const { user, role } = useAuth();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => (await api.get<DashboardResponse>("/dashboard")).data,
  });

  return (
    <div>
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <p className="text-[13px] font-medium text-muted">Selamat datang,</p>
          <h1 className="text-xl font-extrabold text-ink">
            {user?.full_name ?? ""}
          </h1>
        </div>
        {canWrite(role) && (
          <Link
            href="/baby/register"
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary-dark"
          >
            + Daftar Bayi Baru
          </Link>
        )}
      </div>

      <PageState loading={isLoading} error={error} onRetry={() => refetch()}>
        {data && (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard label="Total" count={data.stats.total} tone="primary" icon={<Icon path="M4 6h16M4 12h16M4 18h16" />} />
              <StatCard label="Terisi" count={data.stats.terisi} tone="accent" icon={<Icon path="M12 11a3 3 0 100-6 3 3 0 000 6zM5 21a7 7 0 0114 0" />} />
              <StatCard label="Kosong" count={data.stats.kosong} tone="kosong" icon={<Icon path="M5 12l5 5L20 7" />} />
              <StatCard label="Warning" count={data.stats.warning} tone="warn" icon={<Icon path="M12 9v4m0 4h.01M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z" />} />
            </div>

            <div className="mb-3 mt-7 flex items-center gap-2">
              <h2 className="text-[17px] font-extrabold text-ink">
                Daftar Inkubator
              </h2>
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-bold text-primary">
                {data.incubators.length}
              </span>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {data.incubators.map((it) => (
                <IncubatorCard key={it.incubator_id} item={it} />
              ))}
            </div>
          </>
        )}
      </PageState>
    </div>
  );
}

function IncubatorCard({ item }: { item: IncubatorDashboardItem }) {
  const v = item.latest_vitals;
  return (
    <Link href={`/incubator/${item.incubator_id}`}>
      <Card className="p-4 transition hover:-translate-y-0.5 hover:shadow-soft">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-[15px] font-extrabold text-primary">
            {item.incubator_no}
          </div>
          <div className="min-w-0 flex-1">
            <p
              className={`truncate text-[14.5px] font-bold ${
                item.current_baby ? "text-ink" : "text-muted"
              }`}
            >
              {item.current_baby?.baby_name ?? "Belum ada pasien"}
            </p>
            {item.location && (
              <p className="truncate text-xs text-muted">{item.location}</p>
            )}
          </div>
          <StatusBadge status={item.status} />
        </div>

        {v && (
          <div className="mt-3 grid grid-cols-3 gap-2 border-t border-line pt-3">
            <Vital label="Suhu" value={v.suhu_bayi != null ? `${v.suhu_bayi}°C` : "-"} warn={v.vital_status === "warning"} />
            <Vital label="HR" value={v.heart_rate != null ? `${v.heart_rate} bpm` : "-"} warn={v.vital_status === "warning"} />
            <Vital label="SpO₂" value={v.spo2 != null ? `${v.spo2}%` : "-"} warn={v.vital_status === "warning"} />
          </div>
        )}
      </Card>
    </Link>
  );
}

function Vital({ label, value, warn }: { label: string; value: string; warn: boolean }) {
  return (
    <div className={`rounded-lg px-3 py-1.5 ${warn ? "bg-warn/10" : "bg-kosong/10"}`}>
      <div className="text-[10px] text-muted">{label}</div>
      <div className={`text-[13px] font-extrabold ${warn ? "text-warn" : "text-ink"}`}>
        {value}
      </div>
    </div>
  );
}

function Icon({ path }: { path: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d={path} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
