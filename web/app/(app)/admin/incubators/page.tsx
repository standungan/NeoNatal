"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IncubatorDetail } from "@/lib/types";
import { Card, PageState } from "@/components/ui";
import { formatDateTime } from "@/lib/format";

/**
 * Archived incubators. They are off the dashboard and cannot take a baby, but
 * nothing recorded in them was lost: each opens to its usage history, from which
 * every baby's records are one click away, and can be restored from there.
 */
export default function ArchivedIncubatorsPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["incubators", "archived"],
    queryFn: async () =>
      (await api.get<IncubatorDetail[]>("/incubators", { params: { archived: true } })).data,
  });

  return (
    <div>
      <h1 className="text-xl font-extrabold text-ink">Arsip Inkubator</h1>
      <p className="mt-1 text-sm text-muted">
        Inkubator yang sudah tidak dipakai tetapi pernah ditempati bayi. Riwayatnya tetap
        tersimpan dan inkubator bisa dipulihkan dari halaman detailnya.
      </p>

      <div className="mt-5">
        <PageState loading={isLoading} error={error} onRetry={() => refetch()}>
          {data && data.length === 0 ? (
            <p className="py-16 text-center text-sm text-muted">
              Belum ada inkubator yang diarsipkan.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {data?.map((inc) => (
                <Link key={inc.incubator_id} href={`/incubator/${inc.incubator_id}`}>
                  <Card className="flex items-center gap-3 p-4 transition hover:shadow-soft">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-kosong/15 text-[15px] font-extrabold text-muted">
                      {inc.incubator_no}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[14.5px] font-bold text-ink">
                        Inkubator {inc.incubator_no}
                      </p>
                      <p className="truncate text-xs text-muted">
                        {inc.location ? `${inc.location} · ` : ""}diarsipkan{" "}
                        {formatDateTime(inc.archived_at!)}
                      </p>
                    </div>
                    <span className="text-xs font-semibold text-primary">Lihat riwayat →</span>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </PageState>
      </div>
    </div>
  );
}
