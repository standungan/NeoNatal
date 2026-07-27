"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/components/providers";
import { Spinner } from "@/components/ui";
import { Field, TextInput, Banner, errorMessage } from "@/components/form";

/**
 * Admin-only "+ Tambah Inkubator" button + dialog.
 *
 * Renders nothing for non-admins. This is UX gating only — the real boundary
 * is the backend's `AdminOnly` guard on `POST /api/v1/incubators`, and route
 * access is still enforced server-side regardless of what shows here.
 */
export function AddIncubatorButton() {
  const { role } = useAuth();
  const [open, setOpen] = useState(false);

  if (role !== "admin") return null;

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary-dark"
      >
        + Tambah Inkubator
      </button>
      {open && <AddIncubatorDialog onClose={() => setOpen(false)} />}
    </>
  );
}

function AddIncubatorDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [incubatorNo, setIncubatorNo] = useState("");
  const [location, setLocation] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: async () =>
      api.post("/incubators", {
        incubator_no: incubatorNo.trim(),
        // backend treats location as optional (str | None)
        location: location.trim() || null,
      }),
    onSuccess: () => {
      // refresh the dashboard grid + stat counts so the new incubator shows
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      onClose();
    },
    onError: (e) => setErr(errorMessage(e)),
  });

  const canSubmit = incubatorNo.trim().length > 0 && !save.isPending;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-line bg-card p-6 shadow-card"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-lg font-extrabold text-ink">Tambah Inkubator</h2>
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (canSubmit) save.mutate();
          }}
        >
          <Field label="Nomor Inkubator">
            <TextInput
              placeholder="mis. 08"
              value={incubatorNo}
              onChange={(e) => setIncubatorNo(e.target.value)}
              autoFocus
            />
          </Field>
          <Field label="Lokasi" hint="Opsional — mis. NICU Ruang C">
            <TextInput
              placeholder="NICU Ruang C"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </Field>
          {err && <Banner kind="error">{err}</Banner>}
          <div className="mt-1 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl px-4 py-2 text-sm font-semibold text-muted"
            >
              Batal
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
            >
              {save.isPending && <Spinner className="h-4 w-4" />} Simpan
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
