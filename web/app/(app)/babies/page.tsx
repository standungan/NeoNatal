"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { BabyListItem } from "@/lib/types";
import { Card, PageState } from "@/components/ui";
import { formatDate, formatDateTime, genderLabel } from "@/lib/format";

type Filter = "semua" | "aktif" | "pulang";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "semua", label: "Semua" },
  { key: "aktif", label: "Dirawat" },
  { key: "pulang", label: "Sudah Pulang" },
];

/**
 * Every baby, including those who have gone home.
 *
 * Until this page a baby was reachable only through the incubator they were in,
 * so once discharged — and certainly once the incubator took its next baby —
 * their records existed but no screen led to them. Each row opens the baby's
 * report, which carries their placement, clinical records, sensor history and
 * alerts regardless of where the incubator is now.
 */
export default function BabiesPage() {
  const [filter, setFilter] = useState<Filter>("semua");
  const [input, setInput] = useState("");
  const [q, setQ] = useState("");

  // Search as you type, without a request per keystroke.
  useEffect(() => {
    const t = setTimeout(() => setQ(input.trim()), 300);
    return () => clearTimeout(t);
  }, [input]);

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["babies", filter, q],
    queryFn: async () =>
      (
        await api.get<BabyListItem[]>("/babies", {
          params: { status: filter, q: q || undefined, limit: 200 },
        })
      ).data,
    placeholderData: (prev) => prev,
  });

  return (
    <div>
      <h1 className="text-xl font-extrabold text-ink">Riwayat Bayi</h1>
      <p className="mt-1 text-sm text-muted">
        Semua bayi yang pernah dirawat, termasuk yang sudah pulang. Buka untuk melihat
        laporan, data sensor, dan peringatannya.
      </p>

      <div className="mt-5 flex flex-wrap items-center gap-2.5">
        <div className="flex gap-1.5 rounded-xl border border-line bg-card p-1">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              aria-pressed={filter === f.key}
              onClick={() => setFilter(f.key)}
              className={
                "rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors " +
                (filter === f.key ? "bg-primary text-white" : "text-muted hover:bg-surface hover:text-ink")
              }
            >
              {f.label}
            </button>
          ))}
        </div>
        <input
          type="search"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Cari nama, No. RM, atau No. Registrasi…"
          aria-label="Cari bayi"
          // Full row on phones (it wraps under the filter), shares the row from sm up.
          className="w-full rounded-xl border border-line bg-card px-3.5 py-2 text-sm text-ink outline-none placeholder:text-muted focus:border-primary sm:w-auto sm:min-w-0 sm:max-w-sm sm:flex-1"
        />
      </div>

      <div className="mt-4">
        <PageState loading={isLoading} error={error} onRetry={() => refetch()}>
          {data && data.length === 0 ? (
            <p className="py-16 text-center text-sm text-muted">
              {q ? `Tidak ada bayi yang cocok dengan "${q}".` : "Belum ada data bayi."}
            </p>
          ) : (
            <div className={`flex flex-col gap-2 ${isFetching ? "opacity-70" : ""}`}>
              {data?.map((b) => <BabyRow key={b.baby_id} baby={b} />)}
              {data && data.length >= 200 && (
                <p className="py-2 text-center text-xs text-muted">
                  Menampilkan 200 bayi terbaru — persempit dengan pencarian.
                </p>
              )}
            </div>
          )}
        </PageState>
      </div>
    </div>
  );
}

function BabyRow({ baby }: { baby: BabyListItem }) {
  const p = baby.placement;
  const stay = p && (
    <>
      <span className="whitespace-nowrap">masuk {formatDateTime(p.assigned_at)}</span>
      {p.discharged_at && (
        <span className="whitespace-nowrap">pulang {formatDateTime(p.discharged_at)}</span>
      )}
    </>
  );
  return (
    <Link href={`/baby/${baby.baby_id}/report`}>
      <Card className="flex items-center gap-3 px-4 py-3 transition hover:shadow-soft sm:gap-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-[13px] font-extrabold text-primary">
          {p?.incubator_no ?? "–"}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[14px] font-bold text-ink">{baby.baby_name}</p>
          <p className="truncate text-[12px] text-muted">
            {genderLabel(baby.gender)} · lahir {formatDate(baby.birth_date)}
            {baby.no_rm_bayi ? ` · RM ${baby.no_rm_bayi}` : ""}
            {p?.no_registrasi_nicu ? ` · ${p.no_registrasi_nicu}` : ""}
          </p>
          {/* On phones the stay goes under the name, so the name keeps the width. */}
          {stay && (
            <p className="mt-0.5 flex flex-wrap gap-x-2 text-[12px] text-muted sm:hidden">{stay}</p>
          )}
        </div>
        {stay && (
          <div className="hidden flex-col items-end text-[12px] text-muted sm:flex">{stay}</div>
        )}
        <span
          className={`rounded-full px-2.5 py-0.5 text-[11.5px] font-bold ${
            baby.is_active ? "bg-primary/10 text-primary" : "bg-kosong/15 text-muted"
          }`}
        >
          {baby.is_active ? "Dirawat" : "Pulang"}
        </span>
      </Card>
    </Link>
  );
}
