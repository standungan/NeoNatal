"use client";

import { useEffect, useState } from "react";
import { formatDateTime } from "@/lib/format";
import type { MonitoringRecord } from "@/lib/types";

/**
 * The photo a nurse attached to one monitoring record: a thumbnail that opens
 * full size.
 *
 * Plain <img>, not next/image: these are served by
 * GET /api/v1/monitoring/{id}/photo behind the session cookie, and the image
 * optimizer would fetch that URL server-side without the cookie and get a 403.
 * The backend already returns a small JPEG for `thumb`, so there is nothing for
 * the optimizer to do anyway.
 */
export function MonitoringPhoto({ record }: { record: MonitoringRecord }) {
  const [open, setOpen] = useState(false);
  const src = `/api/v1/monitoring/${record.monitoring_id}/photo`;

  // Esc closes, and the page behind must not scroll while the photo is open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open]);

  const caption = `${formatDateTime(record.observation_time)}${
    record.recorder_name ? ` · ${record.recorder_name}` : ""
  }`;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        title="Lihat foto"
        aria-label={`Lihat foto catatan ${caption}`}
        className="block overflow-hidden rounded-lg border border-line transition hover:border-primary"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`${src}?thumb=true`}
          alt={`Foto catatan ${caption}`}
          loading="lazy"
          className="h-10 w-14 object-cover"
        />
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`Foto catatan ${caption}`}
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-3 bg-black/70 p-4"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={src}
            alt={`Foto catatan ${caption}`}
            onClick={(e) => e.stopPropagation()}
            className="max-h-[80vh] max-w-full rounded-xl bg-card object-contain shadow-card"
          />
          <p className="text-[13px] font-semibold text-white">{caption}</p>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="rounded-xl bg-card px-4 py-2 text-sm font-bold text-ink"
          >
            Tutup
          </button>
        </div>
      )}
    </>
  );
}
