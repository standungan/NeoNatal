import type { IncubatorStatus, Role } from "./types";

/** Roles allowed to create/modify clinical data (mirrors backend PerawatOrAdmin). */
export function canWrite(role: Role | null | undefined): boolean {
  return role === "perawat" || role === "admin";
}

export function formatDate(iso: string, withTime = false): string {
  const d = new Date(iso);
  return d.toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}

export function formatDateTime(iso: string): string {
  return formatDate(iso, true);
}

export const statusMeta: Record<
  IncubatorStatus,
  { label: string; dot: string; bg: string; text: string }
> = {
  terisi: {
    label: "Terisi",
    dot: "bg-primary",
    bg: "bg-primary/10",
    text: "text-primary",
  },
  kosong: {
    label: "Kosong",
    dot: "bg-kosong",
    bg: "bg-kosong/10",
    text: "text-kosong",
  },
  warning: {
    label: "Warning",
    dot: "bg-warn",
    bg: "bg-warn/10",
    text: "text-warn",
  },
  tidak_tersedia: {
    label: "Tidak Tersedia",
    dot: "bg-danger",
    bg: "bg-danger/10",
    text: "text-danger",
  },
};

export function genderLabel(g: string): string {
  return g === "laki_laki" ? "Laki-laki" : "Perempuan";
}

export const roleLabel: Record<string, string> = {
  admin: "Admin",
  perawat: "Perawat",
  dokter: "Dokter",
};
