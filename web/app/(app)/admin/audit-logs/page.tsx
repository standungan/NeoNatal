"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuditLog } from "@/lib/types";
import { Card, PageState } from "@/components/ui";
import { formatDateTime } from "@/lib/format";

function actionTone(action: string): string {
  const a = action.toLowerCase();
  if (a.includes("delete") || a.includes("deactivate")) return "bg-danger/10 text-danger";
  if (a.includes("create")) return "bg-ok/10 text-ok";
  if (a.includes("update") || a.includes("reset")) return "bg-warn/10 text-warn";
  return "bg-primary/10 text-primary";
}

export default function AuditLogsPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: async () =>
      (await api.get<AuditLog[]>("/audit-logs", { params: { limit: 200 } })).data,
  });

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-xl font-extrabold text-ink">Audit Log</h1>
        <button
          onClick={() => refetch()}
          className="rounded-xl border border-line px-4 py-2.5 text-sm font-semibold text-muted hover:bg-surface"
        >
          ↻ Muat Ulang
        </button>
      </div>

      <PageState loading={isLoading} error={error} onRetry={() => refetch()}>
        {data && data.length === 0 ? (
          <p className="py-16 text-center text-muted">
            Belum ada aktivitas tercatat.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {data?.map((log) => (
              <Card key={log.log_id} className="flex items-start gap-3 px-4 py-3">
                <span
                  className={`mt-0.5 rounded-md px-2 py-0.5 text-[11px] font-bold ${actionTone(
                    log.action,
                  )}`}
                >
                  {log.action}
                </span>
                <div className="flex-1">
                  <p className="text-[13px] font-bold text-ink">
                    {log.user_name ?? "Sistem"}
                  </p>
                  {log.table_name && (
                    <p className="text-[11px] text-muted">
                      Tabel: {log.table_name}
                      {log.ip_address ? ` · IP: ${log.ip_address}` : ""}
                    </p>
                  )}
                  <p className="text-[11px] text-muted">
                    {formatDateTime(log.created_at)}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        )}
      </PageState>
    </div>
  );
}
