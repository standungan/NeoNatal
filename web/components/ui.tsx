import Link from "next/link";
import type { ReactNode } from "react";
import type { IncubatorStatus } from "@/lib/types";
import { statusMeta } from "@/lib/format";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-[18px] border border-line bg-card shadow-card ${className}`}
    >
      {children}
    </div>
  );
}

export function StatusBadge({ status }: { status: IncubatorStatus }) {
  const m = statusMeta[status] ?? statusMeta.kosong;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${m.bg} ${m.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${m.dot}`} />
      {m.label}
    </span>
  );
}

export function StatCard({
  label,
  count,
  icon,
  tone,
}: {
  label: string;
  count: number;
  icon: ReactNode;
  tone: "primary" | "accent" | "kosong" | "warn";
}) {
  const tones = {
    primary: "bg-primary/12 text-primary",
    accent: "bg-accent/12 text-accent",
    kosong: "bg-kosong/15 text-kosong",
    warn: "bg-warn/15 text-warn",
  } as const;
  return (
    <Card className="flex flex-col items-center px-3 py-4">
      <div
        className={`flex h-10 w-10 items-center justify-center rounded-xl ${tones[tone]}`}
      >
        {icon}
      </div>
      <div className="mt-2.5 text-2xl font-extrabold leading-none text-ink">
        {count}
      </div>
      <div className="mt-1 text-[11.5px] font-semibold text-muted">{label}</div>
    </Card>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
      role="status"
      aria-label="memuat"
    />
  );
}

export function PageState({
  loading,
  error,
  onRetry,
  children,
}: {
  loading: boolean;
  error?: unknown;
  onRetry?: () => void;
  children: ReactNode;
}) {
  if (loading) {
    return (
      <div className="flex justify-center py-24 text-primary">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 py-24 text-muted">
        <p>Gagal memuat data.</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white"
          >
            Coba Lagi
          </button>
        )}
      </div>
    );
  }
  return <>{children}</>;
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-4 w-1 rounded-sm bg-primary" />
      <h2 className="text-[15px] font-bold text-ink">{children}</h2>
    </div>
  );
}

export function BackLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1 text-sm font-semibold text-muted hover:text-primary"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M15 18l-6-6 6-6"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {label}
    </Link>
  );
}
