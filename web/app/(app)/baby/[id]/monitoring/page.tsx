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
  ScoreChips,
  DateTimeField,
  SubmitButton,
  Banner,
  localNow,
  errorMessage,
} from "@/components/form";
import type { MonitoringRecord } from "@/lib/types";

export default function MonitoringEntryPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const [obsTime, setObsTime] = useState(localNow());
  const [suhuBayi, setSuhuBayi] = useState("");
  const [suhuInk, setSuhuInk] = useState("");
  const [kelembapan, setKelembapan] = useState("");
  const [hr, setHr] = useState("");
  const [rr, setRr] = useState("");
  const [spo2, setSpo2] = useState("");
  const [expression, setExpression] = useState<number | null>(null);
  const [movement, setMovement] = useState<number | null>(null);
  const [pain, setPain] = useState<number | null>(null);
  const [sleepDur, setSleepDur] = useState("");
  const [sleepQuality, setSleepQuality] = useState<number | null>(null);
  const [agitation, setAgitation] = useState("");
  const [catatan, setCatatan] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);

  const num = (s: string) => (s.trim() === "" ? null : Number(s));

  const mutation = useMutation({
    mutationFn: async () => {
      const body = {
        observation_time: new Date(obsTime).toISOString(),
        suhu_bayi: num(suhuBayi),
        suhu_inkubator: num(suhuInk),
        kelembapan_inkubator: num(kelembapan),
        heart_rate: num(hr),
        respiratory_rate: num(rr),
        spo2: num(spo2),
        expression_score: expression,
        movement_score: movement,
        pain_score: pain,
        sleep_duration_min: num(sleepDur),
        sleep_quality: sleepQuality,
        agitation_episodes: num(agitation),
        catatan: catatan.trim() || null,
      };
      const res = await api.post<MonitoringRecord>(`/babies/${id}/monitoring`, body);
      if (photo) {
        const fd = new FormData();
        fd.append("file", photo);
        await api.post(`/monitoring/${res.data.monitoring_id}/photo`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["baby", id] });
      qc.invalidateQueries({ queryKey: ["report", id] });
      router.push(`/baby/${id}/report`);
    },
  });

  return (
    <div>
      <BackLink href={`/baby/${id}/report`} label="Kembali ke Laporan" />
      <h1 className="mb-4 mt-3 text-xl font-extrabold text-ink">Input Tanda Vital</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
        className="flex flex-col gap-4"
      >
        <Card className="flex flex-col gap-4 p-5">
          <DateTimeField label="Waktu Observasi" value={obsTime} onChange={setObsTime} />

          <SectionTitle>Tanda Vital</SectionTitle>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Suhu Bayi (°C)"><NumberInput value={suhuBayi} onChange={(e) => setSuhuBayi(e.target.value)} placeholder="36.8" /></Field>
            <Field label="Suhu Inkubator (°C)"><NumberInput value={suhuInk} onChange={(e) => setSuhuInk(e.target.value)} placeholder="33.5" /></Field>
            <Field label="Kelembapan Inkubator (%)"><NumberInput value={kelembapan} onChange={(e) => setKelembapan(e.target.value)} placeholder="55" /></Field>
            <Field label="Heart Rate (bpm)"><NumberInput value={hr} onChange={(e) => setHr(e.target.value)} placeholder="128" /></Field>
            <Field label="Respiratory Rate (/mnt)"><NumberInput value={rr} onChange={(e) => setRr(e.target.value)} placeholder="48" /></Field>
            <Field label="SpO₂ (%)"><NumberInput value={spo2} onChange={(e) => setSpo2(e.target.value)} placeholder="98" /></Field>
          </div>

          <Field label="Skor Ekspresi (1–5)"><ScoreChips value={expression} onChange={setExpression} min={1} max={5} /></Field>
          <Field label="Skor Gerakan (1–5)"><ScoreChips value={movement} onChange={setMovement} min={1} max={5} /></Field>
          <Field label="Skor Nyeri / NIPS (0–7)" hint="0 = tidak nyeri · ≥ 4 = perlu perhatian">
            <ScoreChips value={pain} onChange={setPain} min={0} max={7} />
          </Field>
        </Card>

        <Card className="flex flex-col gap-4 p-5">
          <SectionTitle>Tidur &amp; Kenyamanan</SectionTitle>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Durasi Tidur (menit)"><NumberInput value={sleepDur} onChange={(e) => setSleepDur(e.target.value)} placeholder="120" /></Field>
            <Field label="Episode Gelisah"><NumberInput value={agitation} onChange={(e) => setAgitation(e.target.value)} placeholder="0" /></Field>
          </div>
          <Field label="Kualitas Tidur (1–5)"><ScoreChips value={sleepQuality} onChange={setSleepQuality} min={1} max={5} /></Field>
        </Card>

        <Card className="flex flex-col gap-4 p-5">
          <Field label="Catatan Observasi (opsional)">
            <TextArea rows={3} value={catatan} onChange={(e) => setCatatan(e.target.value)} placeholder="Catatan observasi..." />
          </Field>
          <Field label="Foto (opsional)" hint="JPEG / PNG / WebP, maks 5 MB">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-primary/10 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-primary"
            />
          </Field>
        </Card>

        {mutation.isError && <Banner kind="error">Gagal menyimpan: {errorMessage(mutation.error)}</Banner>}

        <div className="flex justify-end">
          <SubmitButton loading={mutation.isPending}>Simpan Monitoring</SubmitButton>
        </div>
      </form>
    </div>
  );
}
