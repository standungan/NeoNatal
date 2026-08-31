"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/providers";
import { canWrite } from "@/lib/format";

/**
 * Persistent "Menu Aksi" tab bar for a baby's workspace. Rendered once by
 * baby/[id]/layout.tsx (and reused on the incubator detail page) so switching
 * windows only swaps the content below — the menu never disappears. The tab
 * matching the current route is highlighted (blue).
 */
export function MenuAksiTabs({ babyId }: { babyId: string }) {
  const pathname = usePathname();
  const { role } = useAuth();
  const writable = canWrite(role);

  const tabs = [
    { seg: "report", label: "📊 Laporan", show: true },
    { seg: "monitoring", label: "💓 Input Tanda Vital", show: writable },
    { seg: "observation", label: "🩺 Monitoring Bayi (Observasi)", show: writable },
    { seg: "involvement", label: "👨‍👩‍👧 Keterlibatan", show: writable },
    { seg: "aksi", label: "🤝 Kolaborasi", show: writable },
    { seg: "doctor-note", label: "🩺 Observasi Dokter", show: role === "dokter" },
  ].filter((t) => t.show);

  return (
    <div className="flex flex-wrap gap-2.5">
      {tabs.map((t) => {
        const href = `/baby/${babyId}/${t.seg}`;
        const active = pathname === href;
        return (
          <Link
            key={t.seg}
            href={href}
            aria-current={active ? "page" : undefined}
            className={
              "inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-colors " +
              (active
                ? "bg-primary text-white shadow-sm"
                : "border border-line text-ink hover:bg-surface")
            }
          >
            {t.label}
          </Link>
        );
      })}
    </div>
  );
}
