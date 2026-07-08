"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, SectionTitle, BackLink, PageState } from "@/components/ui";
import {
  Field,
  TextArea,
  ScoreChips,
  DateTimeField,
  SubmitButton,
  Banner,
  localNow,
  errorMessage,
} from "@/components/form";
import { ObservationRadar, categoryColor, categoryFor } from "@/components/observation";
import type { ObservationCatalog, ObservationRecord } from "@/lib/types";

export default function ObservationEntryPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const catalogQ = useQuery({
    queryKey: ["observation-catalog"],
    staleTime: Infinity,
    queryFn: async () => (await api.get<ObservationCatalog>("/observation/catalog")).data,
  });

  const [obsTime, setObsTime] = useState(localNow());
  const [catatan, setCatatan] = useState("");
  const [scores, setScores] = useState<Record<string, number>>({});
  const [showRadar, setShowRadar] = useState(false);
  const setScore = (code: string, v: number) => setScores((s) => ({ ...s, [code]: v }));

  const catalog = catalogQ.data;

  const mutation = useMutation({
    mutationFn: async () => {
      const body = {
        observation_time: new Date(obsTime).toISOString(),
        scores,
        catatan: catatan.trim() || null,
      };
      return (await api.post<ObservationRecord>(`/babies/${id}/observation`, body)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["observation", id] });
      qc.invalidateQueries({ queryKey: ["report", id] });
      router.push(`/baby/${id}/report`);
    },
  });

  // ── live scoring ──────────────────────────────────────────────────────────
  const pillarScores = (catalog?.pillars ?? []).map((p) => {
    const codes = p.items.map((it) => it.item_code);
    const raw = codes.reduce((s, c) => s + (scores[c] ?? 0), 0);
    const max = codes.length * 3;
    return { key: p.key, label: p.label, score: raw, max, percentage: max ? Math.round((raw / max) * 1000) / 10 : 0 };
  });
  const total = pillarScores.reduce((s, p) => s + p.score, 0);
  const maxTotal = catalog?.max_total ?? 162;
  const pct = Math.round((total / maxTotal) * 1000) / 10;
  const category = categoryFor(pct);
  const filled = Object.keys(scores).length;
  const totalItems = catalog?.total_items ?? 54;
  const alarms = (catalog?.pillars ?? []).flatMap((p) =>
    p.items.filter((it) => scores[it.item_code] != null && scores[it.item_code] <= 1),
  );

  return (
    <div>
      <BackLink href={`/baby/${id}/report`} label="Kembali ke Laporan" />
      <h1 className="mb-4 mt-3 text-xl font-extrabold text-ink">Monitoring Bayi</h1>

      <PageState loading={catalogQ.isLoading} error={catalogQ.error} onRetry={() => catalogQ.refetch()}>
        {catalog && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              mutation.mutate();
            }}
            className="flex flex-col gap-4"
          >
            {/* live summary */}
            <Card className="p-5">
              <div className="flex items-center justify-between">
                <SectionTitle>Ringkasan Skor</SectionTitle>
                <button
                  type="button"
                  onClick={() => setShowRadar((v) => !v)}
                  className="text-[13px] font-semibold text-primary hover:underline"
                >
                  {showRadar ? "Sembunyikan radar ▲" : "Tampilkan radar ▼"}
                </button>
              </div>
              <div className={`mt-3 grid grid-cols-1 gap-4 ${showRadar ? "md:grid-cols-2" : ""}`}>
                <div>
                  <div className="flex items-end gap-3">
                    <span className={`text-5xl font-extrabold ${categoryColor(category)}`}>{pct}%</span>
                    <span className={`mb-1 rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold ${categoryColor(category)}`}>
                      {category}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted">
                    {total} / {maxTotal} poin · {filled} / {totalItems} item terisi
                  </p>
                  <p className="mt-3 text-[11px] text-muted">
                    Skala 0–3 per item: <b>0</b> berat · <b>1</b> sedang · <b>2</b> ringan · <b>3</b> normal
                  </p>
                  {alarms.length > 0 && (
                    <div className="mt-3 rounded-xl border border-danger/30 bg-danger/5 p-3">
                      <p className="text-[13px] font-bold text-danger">⚠ {alarms.length} item perlu perhatian (skor 0–1)</p>
                      <ul className="mt-1 max-h-28 overflow-auto text-[12px] text-ink">
                        {alarms.slice(0, 8).map((a) => (
                          <li key={a.item_code} className="truncate">• {a.text}</li>
                        ))}
                        {alarms.length > 8 && <li className="text-muted">…dan {alarms.length - 8} lainnya</li>}
                      </ul>
                    </div>
                  )}
                </div>
                {showRadar && <ObservationRadar pillars={pillarScores} />}
              </div>
            </Card>

            <Card className="p-5">
              <DateTimeField label="Waktu Observasi" value={obsTime} onChange={setObsTime} />
            </Card>

            {/* 8 pillars */}
            {catalog.pillars.map((p, pi) => {
              const ps = pillarScores[pi];
              return (
                <Card key={p.key} className="p-5">
                  <div className="flex items-center justify-between">
                    <SectionTitle>{`${pi + 1}. ${p.label}`}</SectionTitle>
                    <span className="text-[13px] font-bold text-muted">{ps.score}/{ps.max} · {ps.percentage}%</span>
                  </div>
                  <div className="mt-3 flex flex-col gap-3">
                    {p.items.map((it) => (
                      <div key={it.item_code} className="flex flex-col gap-2 border-b border-line pb-3 last:border-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
                        <span className="text-[13.5px] text-ink sm:max-w-[62%]">{it.text}</span>
                        <ScoreChips value={scores[it.item_code] ?? null} onChange={(v) => setScore(it.item_code, v)} min={0} max={3} />
                      </div>
                    ))}
                  </div>
                </Card>
              );
            })}

            <Card className="p-5">
              <Field label="Catatan (opsional)">
                <TextArea rows={3} value={catatan} onChange={(e) => setCatatan(e.target.value)} placeholder="Temuan khusus / catatan observasi..." />
              </Field>
            </Card>

            {mutation.isError && <Banner kind="error">Gagal menyimpan: {errorMessage(mutation.error)}</Banner>}

            <div className="flex items-center justify-end gap-3">
              <span className="text-xs text-muted">{filled} / {totalItems} item terisi</span>
              <SubmitButton loading={mutation.isPending} disabled={filled === 0}>Simpan Monitoring</SubmitButton>
            </div>
          </form>
        )}
      </PageState>
    </div>
  );
}
