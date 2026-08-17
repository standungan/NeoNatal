"use client";

import { type ReactNode } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { BabyDetail } from "@/lib/types";
import { Card, BackLink } from "@/components/ui";
import { MenuAksiTabs } from "@/components/menu-aksi";

/**
 * Workspace shell for a single baby. The incubator/baby header and the Menu
 * Aksi tab bar live here, so they persist while navigating between the child
 * windows (monitoring, observasi, laporan, …) — only {children} swaps.
 */
export default function BabyWorkspaceLayout({ children }: { children: ReactNode }) {
  const { id } = useParams<{ id: string }>();
  const { data: baby } = useQuery({
    queryKey: ["baby", id],
    queryFn: async () => (await api.get<BabyDetail>(`/babies/${id}`)).data,
  });
  const a = baby?.current_assignment;

  return (
    <div>
      <BackLink href="/dashboard" label="Kembali ke Dashboard" />
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
            </p>
          </div>
        </div>
        <div className="mt-4 border-t border-line pt-4">
          <MenuAksiTabs babyId={id} />
        </div>
      </Card>

      {children}
    </div>
  );
}
