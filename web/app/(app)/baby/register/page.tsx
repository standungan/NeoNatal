"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, SectionTitle, BackLink } from "@/components/ui";
import {
  Field,
  TextInput,
  NumberInput,
  TextArea,
  Select,
  SubmitButton,
  Banner,
  errorMessage,
} from "@/components/form";
import type { BabyDetail } from "@/lib/types";

interface AvailableIncubator {
  incubator_id: string;
  incubator_no: string;
  location: string | null;
}

export default function RegisterBabyPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const { data: incubators } = useQuery({
    queryKey: ["incubators", "available"],
    queryFn: async () =>
      (await api.get<AvailableIncubator[]>("/incubators/available")).data,
  });

  const [f, setF] = useState({
    baby_name: "",
    gender: "laki_laki",
    birth_date: "",
    birth_weight: "",
    birth_length: "",
    gestational_age: "",
    birth_type: "",
    clinical_notes: "",
    mother_name: "",
    father_name: "",
    mother_phone: "",
    mother_medical_history: "",
    birth_history: "",
    delivery_history: "",
    additional_notes: "",
    incubator_id: "",
  });
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) =>
    setF((s) => ({ ...s, [k]: e.target.value }));

  const num = (s: string) => (s.trim() === "" ? null : Number(s));

  const mutation = useMutation({
    mutationFn: async () => {
      const body = {
        baby_name: f.baby_name.trim(),
        gender: f.gender,
        birth_date: f.birth_date,
        birth_weight: num(f.birth_weight),
        birth_length: num(f.birth_length),
        gestational_age: num(f.gestational_age),
        birth_type: f.birth_type.trim() || null,
        clinical_notes: f.clinical_notes.trim() || null,
        parent: {
          mother_name: f.mother_name.trim() || null,
          father_name: f.father_name.trim() || null,
          mother_phone: f.mother_phone.trim() || null,
          mother_medical_history: f.mother_medical_history.trim() || null,
          birth_history: f.birth_history.trim() || null,
          delivery_history: f.delivery_history.trim() || null,
          additional_notes: f.additional_notes.trim() || null,
        },
        incubator_id: f.incubator_id,
      };
      return (await api.post<BabyDetail>("/babies", body)).data;
    },
    onSuccess: (baby) => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["incubators", "available"] });
      router.push(`/baby/${baby.baby_id}/report`);
    },
  });

  const valid = f.baby_name.trim() && f.birth_date && f.incubator_id;

  return (
    <div>
      <BackLink href="/dashboard" label="Kembali ke Dashboard" />
      <h1 className="mb-4 mt-3 text-xl font-extrabold text-ink">Registrasi Bayi Baru</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
        className="flex flex-col gap-4"
      >
        <Card className="flex flex-col gap-4 p-5">
          <SectionTitle>Data Bayi</SectionTitle>
          <Field label="Nama Bayi"><TextInput value={f.baby_name} onChange={set("baby_name")} placeholder="Nama bayi" required /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Jenis Kelamin">
              <Select value={f.gender} onChange={set("gender")}>
                <option value="laki_laki">Laki-laki</option>
                <option value="perempuan">Perempuan</option>
              </Select>
            </Field>
            <Field label="Tanggal Lahir"><input type="date" className="input" value={f.birth_date} onChange={set("birth_date")} required /></Field>
            <Field label="Berat Lahir (gram)"><NumberInput value={f.birth_weight} onChange={set("birth_weight")} placeholder="2400" /></Field>
            <Field label="Panjang Lahir (cm)"><NumberInput value={f.birth_length} onChange={set("birth_length")} placeholder="47" /></Field>
            <Field label="Usia Gestasi (minggu)"><NumberInput value={f.gestational_age} onChange={set("gestational_age")} placeholder="36" /></Field>
            <Field label="Jenis Kelahiran"><TextInput value={f.birth_type} onChange={set("birth_type")} placeholder="Normal / Caesar" /></Field>
          </div>
          <Field label="Catatan Klinis (opsional)"><TextArea rows={2} value={f.clinical_notes} onChange={set("clinical_notes")} /></Field>
        </Card>

        <Card className="flex flex-col gap-4 p-5">
          <SectionTitle>Data Orang Tua</SectionTitle>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Nama Ibu"><TextInput value={f.mother_name} onChange={set("mother_name")} /></Field>
            <Field label="Nama Ayah"><TextInput value={f.father_name} onChange={set("father_name")} /></Field>
            <Field label="No. Telepon Ibu"><TextInput value={f.mother_phone} onChange={set("mother_phone")} /></Field>
          </div>
          <Field label="Riwayat Medis Ibu (opsional)"><TextArea rows={2} value={f.mother_medical_history} onChange={set("mother_medical_history")} /></Field>
          <Field label="Riwayat Kelahiran (opsional)"><TextArea rows={2} value={f.birth_history} onChange={set("birth_history")} /></Field>
          <Field label="Riwayat Persalinan (opsional)"><TextArea rows={2} value={f.delivery_history} onChange={set("delivery_history")} /></Field>
          <Field label="Catatan Tambahan (opsional)"><TextArea rows={2} value={f.additional_notes} onChange={set("additional_notes")} /></Field>
        </Card>

        <Card className="flex flex-col gap-4 p-5">
          <SectionTitle>Penempatan Inkubator</SectionTitle>
          <Field label="Pilih Inkubator (kosong)">
            <Select value={f.incubator_id} onChange={set("incubator_id")} required>
              <option value="">— Pilih inkubator —</option>
              {(incubators ?? []).map((inc) => (
                <option key={inc.incubator_id} value={inc.incubator_id}>
                  No. {inc.incubator_no}{inc.location ? ` — ${inc.location}` : ""}
                </option>
              ))}
            </Select>
          </Field>
          {incubators && incubators.length === 0 && (
            <p className="text-[12px] text-warn">Tidak ada inkubator kosong tersedia.</p>
          )}
        </Card>

        {mutation.isError && <Banner kind="error">Gagal menyimpan: {errorMessage(mutation.error)}</Banner>}

        <div className="flex justify-end">
          <SubmitButton loading={mutation.isPending} disabled={!valid}>Daftarkan Bayi</SubmitButton>
        </div>
      </form>
    </div>
  );
}
