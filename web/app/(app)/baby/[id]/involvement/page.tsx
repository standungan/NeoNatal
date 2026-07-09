"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, SectionTitle, BackLink, PageState } from "@/components/ui";
import {
  Field,
  NumberInput,
  TextArea,
  Select,
  ScoreChips,
  DateTimeField,
  SubmitButton,
  Banner,
  localNow,
  errorMessage,
} from "@/components/form";
import { InvolvementRadar, categoryColor, categoryFor } from "@/components/involvement";
import type { InvolvementCatalog, InvolvementRecord } from "@/lib/types";

export default function InvolvementEntryPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const catalogQ = useQuery({
    queryKey: ["involvement-catalog"],
    staleTime: Infinity,
    queryFn: async () => (await api.get<InvolvementCatalog>("/involvement/catalog")).data,
  });

  const [obsTime, setObsTime] = useState(localNow());
  const [scores, setScores] = useState<Record<string, number>>({});
  const [menyusui, setMenyusui] = useState("");
  const [interaksi, setInteraksi] = useState("");
  const [kondisi, setKondisi] = useState("");
  const [catatan, setCatatan] = useState("");
  const setScore = (code: string, v: number) => setScores((s) => ({ ...s, [code]: v }));

  const catalog = catalogQ.data;
  const num = (s: string) => (s.trim() === "" ? null : Number(s));

  const mutation = useMutation({
    mutationFn: async () => {
      const body = {
        observation_time: new Date(obsTime).toISOString(),
        scores,
        catatan: catatan.trim() || null,
        durasi_menyusui: num(menyusui),
        durasi_interaksi: num(interaksi),
        kondisi_bayi: kondisi || null,
      };
      return (await api.post<InvolvementRecord>(`/babies/${id}/involvement`, body)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["baby", id] });
      qc.invalidateQueries({ queryKey: ["report", id] });
      router.push(`/baby/${id}/report`);
    },
  });

  // ── live scoring ──────────────────────────────────────────────────────────
  const items = (catalog?.items ?? []).map((it) => ({
    item_code: it.item_code,
    text: it.text,
    score: scores[it.item_code] ?? 0,
  }));
  const total = items.reduce((s, it) => s + it.score, 0);
  const maxTotal = catalog?.max_total ?? 18;
  const pct = Math.round((total / maxTotal) * 1000) / 10;
  const category = categoryFor(pct);
  const filled = Object.keys(scores).length;
  const totalItems = catalog?.total_items ?? 6;
  const alarms = (catalog?.items ?? []).filter(
    (it) => scores[it.item_code] != null && scores[it.item_code] <= 1,
  );

  return (
    <div>
      <BackLink href={`/baby/${id}/report`} label="Kembali ke Laporan" />
      <h1 className="mb-4 mt-3 text-xl font-extrabold text-ink">Keterlibatan Orang Tua</h1>

      <PageState loading={catalogQ.isLoading} error={catalogQ.error} onRetry={() => catalogQ.refetch()}>
        {catalog && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              mutation.mutate();
            }}
            className="flex flex-col gap-4"
          >
            <Card className="flex flex-col gap-4 p-5">
              <DateTimeField label="Waktu Observasi" value={obsTime} onChange={setObsTime} />
              <p className="text-[12px] text-muted">
                Pilar 6 — {catalog.label}. Nilai tiap item 0–3 (0 = penyimpangan berat · 1 = sedang · 2 = ringan · 3 = sesuai standar).
              </p>
            </Card>

            <Card className="p-5">
              <div className="flex items-center justify-between">
                <SectionTitle>6. {catalog.label}</SectionTitle>
                <span className="text-[13px] font-bold text-muted">{total}/{maxTotal} · {pct}%</span>
              </div>
              <div className="mt-3 flex flex-col gap-3">
                {catalog.items.map((it, i) => (
                  <div key={it.item_code} className="flex flex-col gap-2 border-b border-line pb-3 last:border-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
                    <span className="text-[13.5px] text-ink sm:max-w-[62%]">{i + 1}. {it.text}</span>
                    <ScoreChips value={scores[it.item_code] ?? null} onChange={(v) => setScore(it.item_code, v)} min={0} max={3} />
                  </div>
                ))}
              </div>
            </Card>

            <Card className="flex flex-col gap-4 p-5">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Durasi Menyusui (menit, opsional)"><NumberInput value={menyusui} onChange={(e) => setMenyusui(e.target.value)} placeholder="20" /></Field>
                <Field label="Durasi Interaksi (menit, opsional)"><NumberInput value={interaksi} onChange={(e) => setInteraksi(e.target.value)} placeholder="45" /></Field>
              </div>
              <Field label="Kondisi Bayi Saat Interaksi">
                <Select value={kondisi} onChange={(e) => setKondisi(e.target.value)}>
                  <option value="">Pilih kondisi bayi</option>
                  <option value="Tenang">Tenang</option>
                  <option value="Aktif">Aktif</option>
                  <option value="Rewel">Rewel</option>
                  <option value="Tidur">Tidur</option>
                </Select>
              </Field>
              <Field label="Catatan (opsional)">
                <TextArea rows={3} value={catatan} onChange={(e) => setCatatan(e.target.value)} placeholder="Catatan kerjasama & keterlibatan keluarga..." />
              </Field>
            </Card>

            {/* live summary */}
            <Card className="p-5">
              <SectionTitle>Ringkasan Skor</SectionTitle>
              <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
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
                  {alarms.length > 0 && (
                    <div className="mt-3 rounded-xl border border-danger/30 bg-danger/5 p-3">
                      <p className="text-[13px] font-bold text-danger">⚠ {alarms.length} item perlu perhatian (skor 0–1)</p>
                      <ul className="mt-1 text-[12px] text-ink">
                        {alarms.map((a) => (
                          <li key={a.item_code} className="truncate">• {a.text}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
                <InvolvementRadar items={items} />
              </div>
            </Card>

            {mutation.isError && <Banner kind="error">Gagal menyimpan: {errorMessage(mutation.error)}</Banner>}

            <div className="flex items-center justify-end gap-3">
              <span className="text-xs text-muted">{filled} / {totalItems} item terisi</span>
              <SubmitButton loading={mutation.isPending} disabled={filled === 0}>Simpan Keterlibatan</SubmitButton>
            </div>
          </form>
        )}
      </PageState>
    </div>
  );
}
