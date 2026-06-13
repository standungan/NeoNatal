"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { useAuth } from "@/components/providers";
import { roleLabel } from "@/lib/format";

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, role, logout } = useAuth();
  const [adminOpen, setAdminOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line bg-card/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-5">
          <Link href="/dashboard" className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-white">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path
                  d="M12 11a3 3 0 100-6 3 3 0 000 6zM5 21a7 7 0 0114 0"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </span>
            <span className="text-[15px] font-extrabold text-ink">
              Neonatal Care
            </span>
          </Link>

          <nav className="ml-4 hidden items-center gap-1 sm:flex">
            <Link
              href="/dashboard"
              className="rounded-lg px-3 py-2 text-sm font-semibold text-muted hover:bg-surface hover:text-ink"
            >
              Dashboard
            </Link>

            {role === "admin" && (
              <div
                className="relative"
                onMouseLeave={() => setAdminOpen(false)}
              >
                <button
                  onClick={() => setAdminOpen((o) => !o)}
                  className="rounded-lg px-3 py-2 text-sm font-semibold text-muted hover:bg-surface hover:text-ink"
                >
                  Admin ▾
                </button>
                {adminOpen && (
                  <div className="absolute left-0 mt-1 w-52 overflow-hidden rounded-xl border border-line bg-card shadow-card">
                    <Link
                      href="/admin/users"
                      className="block px-4 py-2.5 text-sm hover:bg-surface"
                      onClick={() => setAdminOpen(false)}
                    >
                      Manajemen Pengguna
                    </Link>
                    <Link
                      href="/admin/audit-logs"
                      className="block px-4 py-2.5 text-sm hover:bg-surface"
                      onClick={() => setAdminOpen(false)}
                    >
                      Audit Log
                    </Link>
                  </div>
                )}
              </div>
            )}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <div className="text-[13px] font-bold leading-tight text-ink">
                {user?.full_name ?? ""}
              </div>
              <div className="text-[11px] text-muted">
                {role ? roleLabel[role] : ""}
              </div>
            </div>
            <button
              onClick={logout}
              className="rounded-lg border border-line px-3 py-2 text-sm font-semibold text-muted hover:bg-surface hover:text-danger"
            >
              Keluar
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-6">{children}</main>
    </div>
  );
}
