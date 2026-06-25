"use client";

import type { ReactNode } from "react";
import { Spinner } from "@/components/ui";

/** Label + optional hint wrapping any field control. */
export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] font-semibold text-ink">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-muted">{hint}</span>}
    </label>
  );
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`input ${props.className ?? ""}`} />;
}

export function NumberInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input inputMode="decimal" {...props} className={`input ${props.className ?? ""}`} />;
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`input ${props.className ?? ""}`} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`input ${props.className ?? ""}`} />;
}

/** Datetime-local input. Value/onChange handle a local-time string; convert to ISO on submit. */
export function DateTimeField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <Field label={label}>
      <input
        type="datetime-local"
        className="input"
        value={value}
        max={localNow()}
        onChange={(e) => onChange(e.target.value)}
      />
    </Field>
  );
}

/** Current local time formatted for <input type="datetime-local"> (YYYY-MM-DDTHH:mm). */
export function localNow(): string {
  const d = new Date();
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60_000).toISOString().slice(0, 16);
}

/** Ranged 0..N (or 1..N) chip selector — mirrors the Flutter ScoreChips. */
export function ScoreChips({
  value,
  onChange,
  min = 1,
  max = 5,
}: {
  value: number | null;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
}) {
  const items = Array.from({ length: max - min + 1 }, (_, i) => min + i);
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((n) => {
        const selected = value === n;
        return (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            className={`flex h-10 w-10 items-center justify-center rounded-full border text-sm font-bold transition ${
              selected
                ? "border-primary bg-primary text-white shadow-soft"
                : "border-line bg-[#f8fafc] text-muted hover:border-primary/40"
            }`}
          >
            {n}
          </button>
        );
      })}
    </div>
  );
}

export function SubmitButton({
  loading,
  children,
  disabled,
}: {
  loading: boolean;
  children: ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      type="submit"
      disabled={loading || disabled}
      className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-bold text-white transition hover:bg-primary-dark disabled:opacity-60"
    >
      {loading && <Spinner className="h-4 w-4" />}
      {children}
    </button>
  );
}

/** Inline error/success banner. */
export function Banner({ kind, children }: { kind: "error" | "success"; children: ReactNode }) {
  const tone =
    kind === "error"
      ? "border-danger/30 bg-danger/10 text-danger"
      : "border-ok/30 bg-ok/10 text-ok";
  return (
    <div className={`rounded-xl border px-4 py-2.5 text-sm font-semibold ${tone}`}>{children}</div>
  );
}

/** Pull a human-readable message out of an Axios/FastAPI error. */
export function errorMessage(e: unknown): string {
  const anyE = e as { response?: { data?: { detail?: unknown } }; message?: string };
  const detail = anyE?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return anyE?.message ?? "Terjadi kesalahan";
}
