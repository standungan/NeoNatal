"use client";

import { type ReactNode } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { latestPlacement, type BabyDetail } from "@/lib/types";
import { Card, BackLink } from "@/components/ui";
import { MenuAksiTabs } from "@/components/menu-aksi";
import { formatDateTime } from "@/lib/format";

/**
 * Workspace shell for a single baby. The incubator/baby header and the Menu
 * Aksi tab bar live here, so they persist while navigating between the child
 * windows (monitoring, observasi, laporan, …) — only {children} swaps.
 *
 * A discharged baby is reached from Riwayat Bayi, so the header says where and
 * when they were treated, and only the report is offered — the entry forms are
 * for a baby who is still in an incubator.
 */
export default function BabyWorkspaceLayout({ children }: { children: ReactNode }) {
  const { id } = useParams<{ id: string }>();
  const { data: baby } = useQuery({
    queryKey: ["baby", id],
    queryFn: async () => (await api.get<BabyDetail>(`/babies/${id}`)).data,
  });
  const a = baby ? latestPlacement(baby) : null;
  const discharged = baby ? !baby.is_active : false;

  return (
    <div>
      {discharged ? (
        <BackLink href="/babies" label="Kembali ke Riwayat Bayi" />
      ) : (
        <BackLink href="/dashboard" label="Kembali ke Dashboard" />
      )}
      <Card className="mb-4 mt-3 p-4">
        <div className="flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-base font-extrabold text-primary">
            {a?.incubator_no ?? "–"}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-base font-extrabold text-ink">
              {baby?.baby_name ?? "Memuat…"}
            </p>
            <p className="text-sm text-muted">
              {a ? `Inkubator ${a.incubator_no}${a.location ? ` — ${a.location}` : ""}` : "—"}
              {discharged && a?.discharged_at && ` · pulang ${formatDateTime(a.discharged_at)}`}
            </p>
          </div>
          {discharged && (
            <span className="shrink-0 rounded-full bg-kosong/15 px-2.5 py-1 text-xs font-bold text-muted">
              Sudah pulang
            </span>
          )}
        </div>
        <div className="mt-4 border-t border-line pt-4">
          <MenuAksiTabs babyId={id} discharged={discharged} />
        </div>
      </Card>

      {children}
    </div>
  );
}
