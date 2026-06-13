"use client";

import { useState } from "react";
import { loginRequest } from "@/lib/api";
import { Card, Spinner } from "@/components/ui";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await loginRequest(email.trim(), password);
      window.location.href = "/dashboard";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login gagal");
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="w-full max-w-[420px]">
        <div className="flex flex-col items-center">
          <div
            className="flex h-[76px] w-[76px] items-center justify-center rounded-[22px] bg-primary text-white"
            style={{ boxShadow: "0 12px 28px -6px rgba(37,99,235,0.55)" }}
          >
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path
                d="M12 11a3 3 0 100-6 3 3 0 000 6zM5 21a7 7 0 0114 0"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <h1 className="mt-5 text-[23px] font-extrabold text-ink">
            Neonatal Care System
          </h1>
          <p className="mt-1.5 text-[13px] text-muted">
            Sistem Monitoring Bayi pada Inkubator
          </p>
        </div>

        <Card className="mt-7 p-6">
          <h2 className="text-base font-bold text-ink">Masuk ke akun Anda</h2>
          <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-3.5">
            <Field label="Email">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Masukkan email Anda"
                className="input"
              />
            </Field>
            <Field label="Password">
              <div className="relative">
                <input
                  type={show ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Masukkan password Anda"
                  className="input pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShow((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-ink"
                  aria-label="tampilkan password"
                >
                  {show ? "🙈" : "👁"}
                </button>
              </div>
            </Field>

            {error && (
              <div className="flex items-center gap-2 rounded-xl bg-danger/8 px-3 py-2.5 text-[13px] text-danger">
                <span aria-hidden>⚠</span>
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="mt-1 flex h-[52px] items-center justify-center rounded-[14px] bg-primary text-[15px] font-bold text-white transition hover:bg-primary-dark disabled:opacity-60"
            >
              {loading ? <Spinner className="h-5 w-5" /> : "Masuk"}
            </button>
          </form>
        </Card>

        <p className="mt-5 text-center text-xs text-muted">
          🛡 Akses terbatas — hanya untuk petugas berwenang.
        </p>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[13px] font-medium text-muted">{label}</span>
      {children}
    </label>
  );
}
