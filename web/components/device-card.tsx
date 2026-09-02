"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/components/providers";
import { errorMessage } from "@/components/form";
import { Card, SectionTitle, Spinner } from "@/components/ui";
import { formatDate } from "@/lib/format";
import {
  isDeviceOnline,
  type Device,
  type DeviceProvisionResponse,
} from "@/lib/types";

/**
 * IoT sensor unit bound to one incubator.
 *
 * Everyone sees the status strip — a nurse needs to know whether the vitals
 * feed is live before trusting a flat reading — but only an admin can
 * provision or revoke. UX gating only; the real boundary is the backend's
 * AdminOnly guard on POST/DELETE /incubators/{id}/device.
 */
export function DeviceCard({ incubatorId }: { incubatorId: string }) {
  const qc = useQueryClient();
  const { role } = useAuth();
  const isAdmin = role === "admin";

  // The plaintext key, held only in component state and only until the admin
  // navigates away. It is never refetchable — see the panel below.
  const [mintedKey, setMintedKey] = useState<string | null>(null);
  const [confirmingRevoke, setConfirmingRevoke] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const q = useQuery({
    queryKey: ["device", incubatorId],
    queryFn: async () =>
      (await api.get<Device | null>(`/incubators/${incubatorId}/device`)).data,
    // Keeps the online/offline dot honest without a manual refresh.
    refetchInterval: 15_000,
  });

  const provision = useMutation({
    mutationFn: async () =>
      (
        await api.post<DeviceProvisionResponse>(
          `/incubators/${incubatorId}/device`,
          {},
        )
      ).data,
    onSuccess: (d) => {
      setErr(null);
      setMintedKey(d.device_key);
      qc.invalidateQueries({ queryKey: ["device", incubatorId] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e) => setErr(errorMessage(e)),
  });

  const revoke = useMutation({
    mutationFn: async () =>
      api.delete(`/incubators/${incubatorId}/device`),
    onSuccess: () => {
      setErr(null);
      setMintedKey(null);
      setConfirmingRevoke(false);
      qc.invalidateQueries({ queryKey: ["device", incubatorId] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e) => setErr(errorMessage(e)),
  });

  if (q.isLoading) {
    return (
      <Card className="p-5">
        <SectionTitle>Perangkat IoT</SectionTitle>
        <div className="flex justify-center py-6">
          <Spinner />
        </div>
      </Card>
    );
  }

  const device = q.data ?? null;

  return (
    <Card className="p-5">
      {/* Title and the admin action share one row: this is a status strip, not
          a form, so it should not occupy a form's worth of vertical space.
          items-START, not center: the button is taller than the title, and
          centring would push the title a few px below where it sits in every
          other card on the page. */}
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <SectionTitle>Perangkat IoT</SectionTitle>

        {isAdmin && !device && (
          <button
            onClick={() => provision.mutate()}
            disabled={provision.isPending}
            className="flex items-center gap-2 rounded-lg bg-primary px-3 py-1 text-[12.5px] font-bold text-white disabled:opacity-60"
          >
            {provision.isPending && <Spinner className="h-3.5 w-3.5" />}
            Pasang Perangkat
          </button>
        )}
        {isAdmin && device && !confirmingRevoke && (
          <button
            onClick={() => setConfirmingRevoke(true)}
            className="rounded-lg border border-line px-3 py-1 text-[12.5px] font-bold text-danger hover:bg-surface"
          >
            Lepas Perangkat
          </button>
        )}
      </div>

      {device ? (
        <DeviceStatus device={device} />
      ) : (
        <p className="mt-2 text-sm text-muted">
          Belum ada perangkat terpasang pada inkubator ini. Data tanda vital
          hanya berasal dari input manual.
        </p>
      )}

      {mintedKey && <MintedKeyPanel deviceKey={mintedKey} onDismiss={() => setMintedKey(null)} />}

      {err && (
        <p className="mt-3 text-sm font-semibold text-danger">{err}</p>
      )}

      {isAdmin && device && !confirmingRevoke && (
        <AllowlistRow incubatorId={incubatorId} device={device} />
      )}

      {isAdmin && device && confirmingRevoke && (
        <div className="mt-3 rounded-xl border border-danger/30 bg-danger/5 p-3.5">
          <p className="text-[13px] font-bold text-ink">
            Lepas perangkat dari inkubator ini?
          </p>
          <p className="mt-1 text-[12.5px] leading-relaxed text-muted">
            Kunci perangkat lama langsung tidak berlaku. Memasang perangkat lagi
            akan menghasilkan kunci <strong>baru</strong>, dan alat harus
            di-<em>flash</em> ulang dengan kunci itu sebelum bisa mengirim data.
            Riwayat pembacaan sensor tetap tersimpan.
          </p>
          <div className="mt-2.5 flex gap-2">
            <button
              onClick={() => revoke.mutate()}
              disabled={revoke.isPending}
              className="flex items-center gap-2 rounded-xl bg-danger px-3.5 py-1.5 text-[13px] font-bold text-white disabled:opacity-60"
            >
              {revoke.isPending && <Spinner className="h-3.5 w-3.5" />}
              Ya, lepas
            </button>
            <button
              onClick={() => setConfirmingRevoke(false)}
              className="rounded-xl border border-line px-3.5 py-1.5 text-[13px] font-bold text-ink hover:bg-surface"
            >
              Batal
            </button>
          </div>
        </div>
      )}
    </Card>
  );
}

function DeviceStatus({ device }: { device: Device }) {
  // Recompute on a timer: last_seen_at is a timestamp, so "online" decays even
  // when no new data arrives and the component would otherwise not re-render.
  const [, tick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 5_000);
    return () => clearInterval(id);
  }, []);

  const online = isDeviceOnline(device.last_seen_at);

  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px]">
      <span
        aria-hidden
        className={"h-2 w-2 shrink-0 rounded-full " + (online ? "bg-ok" : "bg-danger")}
      />
      <span className="font-bold text-ink">
        {online ? "Online" : device.last_seen_at ? "Offline" : "Belum pernah mengirim data"}
      </span>
      {device.label && (
        <>
          <span aria-hidden className="text-line">·</span>
          <span className="truncate text-muted">{device.label}</span>
        </>
      )}
      {device.last_ip && (
        <>
          <span aria-hidden className="text-line">·</span>
          <span className="font-mono text-[12px] text-muted">{device.last_ip}</span>
        </>
      )}
      {device.last_seen_at && (
        <>
          <span aria-hidden className="text-line">·</span>
          <span className="text-muted">
            terakhir kirim {formatDate(device.last_seen_at, true)}
          </span>
        </>
      )}
      <span aria-hidden className="text-line">·</span>
      <span className="text-muted">dipasang {formatDate(device.created_at, true)}</span>
    </div>
  );
}

/**
 * The one and only moment the plaintext key exists outside the firmware.
 * The server keeps just its SHA-256, so there is no "show again" — losing it
 * means revoke, re-provision, and physically reflashing the board.
 */
function MintedKeyPanel({
  deviceKey,
  onDismiss,
}: {
  deviceKey: string;
  onDismiss: () => void;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(deviceKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard can be blocked (insecure origin, permissions). The key is
      // selectable on screen, so this is a convenience, not the only route.
      setCopied(false);
    }
  }

  return (
    <div className="mt-4 rounded-xl border border-warn/40 bg-warn/5 p-4">
      <p className="text-sm font-extrabold text-ink">
        Salin kunci ini sekarang
      </p>
      <p className="mt-1 text-[13px] leading-relaxed text-muted">
        Kunci hanya ditampilkan <strong>satu kali</strong> — server menyimpan
        ringkasannya saja, jadi tidak bisa dilihat lagi. Kunci ini dipakai
        firmware terautentikasi: dikirim sebagai header{" "}
        <code className="rounded bg-surface px-1 py-0.5">X-Device-Key</code> ke{" "}
        <code className="rounded bg-surface px-1 py-0.5">/api/v1/telemetry</code>.
      </p>
      <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted">
        Rig yang sekarang mengirim lewat <em>payload label</em> belum
        membutuhkannya — simpan saja untuk nanti. Kalau hilang, perangkat harus
        dilepas dan dipasang ulang untuk mendapat kunci baru.
      </p>

      <div className="mt-3 flex items-center gap-2">
        <code className="flex-1 select-all break-all rounded-lg border border-line bg-white px-3 py-2 font-mono text-[13px] text-ink">
          {deviceKey}
        </code>
        <button
          onClick={copy}
          className="shrink-0 rounded-xl border border-line px-3 py-2 text-sm font-bold text-ink hover:bg-surface"
        >
          {copied ? "Tersalin" : "Salin"}
        </button>
      </div>

      <button
        onClick={onDismiss}
        className="mt-3 text-[13px] font-semibold text-muted underline hover:text-ink"
      >
        Sudah saya simpan
      </button>
    </div>
  );
}

/**
 * Optional IP filter for the unauthenticated legacy ingest route.
 *
 * This is NOT how an incubator is coupled to its device — that is the device key
 * on the authenticated path, or the payload label on the legacy one. IP only
 * narrows who may reach an already-unauthenticated endpoint, and DHCP can move
 * it at any time, so it is presented as an optional safety net rather than
 * something the system depends on.
 */
function AllowlistRow({
  incubatorId,
  device,
}: {
  incubatorId: string;
  device: Device;
}) {
  const qc = useQueryClient();
  const [value, setValue] = useState(device.allowed_ip ?? "");
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: async () =>
      api.put(`/incubators/${incubatorId}/device`, { allowed_ip: value.trim() }),
    onSuccess: () => {
      setErr(null);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      qc.invalidateQueries({ queryKey: ["device", incubatorId] });
    },
    onError: (e) => setErr(errorMessage(e)),
  });

  const [open, setOpen] = useState(Boolean(device.allowed_ip));

  // Collapsed by default: this is optional hardening, not something an operator
  // reads at a glance, and the card's job is to be a compact status strip.
  // Auto-expanded when a filter IS set, so an active restriction is never hidden.
  if (!open) {
    return (
      <div className="mt-3 flex items-center gap-2 border-t border-line pt-3">
        <button
          onClick={() => setOpen(true)}
          className="text-[12.5px] font-semibold text-primary underline"
        >
          Batasi alamat pengirim
        </button>
        <span className="text-[12px] text-muted">
          (opsional — saat ini menerima dari mana saja)
        </span>
      </div>
    );
  }

  return (
    <div className="mt-3 border-t border-line pt-3">
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-[12.5px] font-semibold text-muted" htmlFor="allowed-ip">
          Batasi alamat pengirim
        </label>
        <input
          id="allowed-ip"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={device.last_ip ?? "mis. 192.168.0.0/24"}
          className="w-52 rounded-lg border border-line px-2.5 py-1 font-mono text-[12.5px] outline-none focus:border-primary"
        />
        <button
          onClick={() => save.mutate()}
          disabled={save.isPending}
          className="rounded-lg border border-line px-3 py-1 text-[12.5px] font-bold text-ink hover:bg-surface disabled:opacity-60"
        >
          {saved ? "Tersimpan" : "Simpan"}
        </button>
        {device.last_ip && value !== device.last_ip && (
          <button
            onClick={() => setValue(device.last_ip!)}
            className="text-[12px] font-semibold text-primary underline"
          >
            pakai {device.last_ip}
          </button>
        )}
      </div>
      <p className="mt-1.5 text-[11.5px] leading-relaxed text-muted">
        Satu alamat atau CIDR. Kosongkan untuk menerima dari mana saja. Ini hanya
        penyaring tambahan untuk firmware lama yang belum memakai kunci perangkat —
        <strong> bukan</strong> cara inkubator dipasangkan ke alat.
      </p>
      {err && <p className="mt-1 text-[12.5px] font-semibold text-danger">{err}</p>}
    </div>
  );
}
