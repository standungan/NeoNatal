"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { DoctorNote } from "@/lib/types";
import { Card, PageState, SectionTitle, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { errorMessage } from "@/components/form";

export default function DoctorNotePage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [catatan, setCatatan] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const notesQ = useQuery({
    queryKey: ["doctor-notes", id],
    queryFn: async () =>
      (await api.get<DoctorNote[]>(`/babies/${id}/doctor-notes`)).data,
  });

  const save = useMutation({
    mutationFn: async () =>
      api.post(`/babies/${id}/doctor-notes`, {
        observation_time: new Date().toISOString(),
        catatan: catatan.trim(),
      }),
    onSuccess: () => {
      setCatatan("");
      setErr(null);
      qc.invalidateQueries({ queryKey: ["doctor-notes", id] });
      qc.invalidateQueries({ queryKey: ["report", id] });
    },
    onError: (e) => setErr(errorMessage(e)),
  });

  const canSubmit = catatan.trim().length > 0 && !save.isPending;

  return (
    <div>
      <h1 className="mb-4 mt-3 text-xl font-extrabold text-ink">Observasi Dokter</h1>

      <div className="flex flex-col gap-4">
        <Card className="p-5">
          <SectionTitle>Catatan Observasi</SectionTitle>
          <form
            className="mt-4 flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (canSubmit) save.mutate();
            }}
          >
            <textarea
              className="min-h-[140px] w-full rounded-xl border border-line px-3.5 py-2.5 text-sm text-ink outline-none focus:border-primary"
              placeholder="Tulis catatan observasi dokter terhadap inkubator dan bayi…"
              value={catatan}
              onChange={(e) => setCatatan(e.target.value)}
              autoFocus
            />
            {err && <p className="text-[13px] text-danger">{err}</p>}
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!canSubmit}
                className="flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white disabled:opacity-60"
              >
                {save.isPending && <Spinner className="h-4 w-4" />} Simpan Catatan
              </button>
            </div>
          </form>
        </Card>

        <Card className="p-5">
          <SectionTitle>Riwayat Catatan</SectionTitle>
          <PageState
            loading={notesQ.isLoading}
            error={notesQ.error}
            onRetry={() => notesQ.refetch()}
          >
            {notesQ.data && notesQ.data.length > 0 ? (
              <div className="mt-3 flex flex-col gap-3">
                {notesQ.data.map((n) => (
                  <div key={n.note_id} className="rounded-xl border border-line p-3.5">
                    <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-ink">
                      {n.catatan}
                    </p>
                    <p className="mt-2 text-xs text-muted">
                      {n.recorder_name ? `${n.recorder_name} · ` : ""}
                      {formatDateTime(n.observation_time)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted">Belum ada catatan.</p>
            )}
          </PageState>
        </Card>
      </div>
    </div>
  );
}
