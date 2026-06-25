"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, SectionTitle, BackLink } from "@/components/ui";
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
import type { InvolvementRecord } from "@/lib/types";

const DOMAINS: { key: string; title: string; subtitle: string }[] = [
  { key: "presence_score", title: "Kehadiran", subtitle: "Frekuensi & durasi kunjungan" },
  { key: "physical_interaction_score", title: "Interaksi Fisik", subtitle: "Sentuhan, menggendong, kangaroo care" },
  { key: "feeding_participation_score", title: "Partisipasi Menyusui", subtitle: "Menyusui langsung / ASI perah" },
  { key: "care_participation_score", title: "Partisipasi Perawatan", subtitle: "Ganti popok, kebersihan, menenangkan" },
  { key: "knowledge_score", title: "Pengetahuan", subtitle: "Pemahaman kondisi & rencana perawatan" },
  { key: "communication_score", title: "Komunikasi", subtitle: "Keterlibatan saat diskusi klinis" },
  { key: "emotional_readiness_score", title: "Kesiapan Emosional", subtitle: "Kecemasan & kepercayaan diri" },
  { key: "discharge_readiness_score", title: "Kesiapan Pulang", subtitle: "Kompetensi perawatan & kesadaran darurat" },
];

function category(score: number): string {
  if (score >= 76) return "Sangat Baik";
  if (score >= 51) return "Baik";
  if (score >= 26) return "Sedang";
  return "Rendah";
}

export default function InvolvementEntryPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const [obsTime, setObsTime] = useState(localNow());
  const [scores, setScores] = useState<Record<string, number | null>>(
    Object.fromEntries(DOMAINS.map((d) => [d.key, null])),
  );
  const [menyusui, setMenyusui] = useState("");
  const [interaksi, setInteraksi] = useState("");
  const [kondisi, setKondisi] = useState("");
  const [catatan, setCatatan] = useState("");

  const raw = DOMAINS.reduce((sum, d) => sum + (scores[d.key] ?? 0), 0);
  const pei = Math.round((raw / 32) * 100);
  const peiColor =
    pei >= 76 ? "text-ok" : pei >= 51 ? "text-primary" : pei >= 26 ? "text-warn" : "text-kosong";

  const num = (s: string) => (s.trim() === "" ? null : Number(s));

  const mutation = useMutation({
    mutationFn: async () => {
      const body = {
        observation_time: new Date(obsTime).toISOString(),
        durasi_menyusui: num(menyusui),
        durasi_interaksi: num(interaksi),
        ...scores,
        kondisi_bayi: kondisi || null,
        catatan: catatan.trim() || null,
      };
      return (await api.post<InvolvementRecord>(`/babies/${id}/involvement`, body)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["baby", id] });
      qc.invalidateQueries({ queryKey: ["report", id] });
      router.push(`/baby/${id}/report`);
    },
  });

  return (
    <div>
      <BackLink href={`/baby/${id}/report`} label="Kembali ke Laporan" />
      <h1 className="mb-4 mt-3 text-xl font-extrabold text-ink">Input Keterlibatan Orang Tua</h1>

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
            Nilai tiap domain 0–4 (0 = tidak ada · 1 = minimal · 2 = kadang · 3 = sering · 4 = konsisten)
          </p>
        </Card>

        <Card className="flex flex-col gap-3 p-5">
          <SectionTitle>8 Domain FICare</SectionTitle>
          {DOMAINS.map((d, i) => (
            <div key={d.key} className="rounded-xl border border-line bg-[#f8fafc] p-3.5">
              <div className="flex items-center gap-2.5">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-white">
                  {i + 1}
                </span>
                <div>
                  <p className="text-[13.5px] font-bold text-ink">{d.title}</p>
                  <p className="text-[11.5px] text-muted">{d.subtitle}</p>
                </div>
              </div>
              <div className="mt-3">
                <ScoreChips
                  value={scores[d.key]}
                  onChange={(v) => setScores((s) => ({ ...s, [d.key]: v }))}
                  min={0}
                  max={4}
                />
              </div>
            </div>
          ))}
        </Card>

        <Card className="flex flex-col gap-3 p-5">
          <SectionTitle>Parent Engagement Index</SectionTitle>
          <div className="flex items-center gap-3">
            <span className={`text-4xl font-extrabold ${peiColor}`}>{pei}</span>
            <span className="text-lg text-muted">/ 100</span>
            <span className={`rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold ${peiColor}`}>
              {category(pei)}
            </span>
          </div>
          <p className="text-[11px] text-muted">
            0–25 Rendah · 26–50 Sedang · 51–75 Baik · 76–100 Sangat Baik
          </p>
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
            <TextArea rows={3} value={catatan} onChange={(e) => setCatatan(e.target.value)} placeholder="Catatan aktivitas dan interaksi orang tua..." />
          </Field>
        </Card>

        {mutation.isError && <Banner kind="error">Gagal menyimpan: {errorMessage(mutation.error)}</Banner>}

        <div className="flex justify-end">
          <SubmitButton loading={mutation.isPending}>Simpan Keterlibatan</SubmitButton>
        </div>
      </form>
    </div>
  );
}
