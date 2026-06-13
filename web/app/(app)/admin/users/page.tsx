"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ManagedUser, Role } from "@/lib/types";
import { Card, PageState, Spinner } from "@/components/ui";
import { roleLabel } from "@/lib/format";

export default function UsersPage() {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<
    | { mode: "create" }
    | { mode: "edit"; user: ManagedUser }
    | { mode: "reset"; user: ManagedUser }
    | null
  >(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["users"],
    queryFn: async () => (await api.get<ManagedUser[]>("/users")).data,
  });

  const toggle = useMutation({
    mutationFn: async (u: ManagedUser) =>
      u.is_active
        ? api.delete(`/users/${u.id}`)
        : api.put(`/users/${u.id}`, { is_active: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-xl font-extrabold text-ink">Manajemen Pengguna</h1>
        <button
          onClick={() => setDialog({ mode: "create" })}
          className="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary-dark"
        >
          + Tambah Pengguna
        </button>
      </div>

      <PageState loading={isLoading} error={error} onRetry={() => refetch()}>
        <div className="flex flex-col gap-2.5">
          {data?.map((u) => (
            <Card key={u.id} className="flex items-center gap-3 p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 font-bold text-primary">
                {u.full_name.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-bold text-ink">{u.full_name}</p>
                <p className="truncate text-xs text-muted">{u.email}</p>
                <div className="mt-1 flex gap-1.5">
                  <Tag className="bg-primary/10 text-primary">
                    {roleLabel[u.role]}
                  </Tag>
                  <Tag
                    className={
                      u.is_active
                        ? "bg-ok/10 text-ok"
                        : "bg-kosong/15 text-kosong"
                    }
                  >
                    {u.is_active ? "Aktif" : "Nonaktif"}
                  </Tag>
                </div>
              </div>
              <div className="flex shrink-0 gap-1.5">
                <SmallBtn onClick={() => setDialog({ mode: "edit", user: u })}>
                  Edit
                </SmallBtn>
                <SmallBtn onClick={() => setDialog({ mode: "reset", user: u })}>
                  Reset PW
                </SmallBtn>
                <SmallBtn
                  onClick={() => toggle.mutate(u)}
                  className={u.is_active ? "text-danger" : "text-ok"}
                >
                  {u.is_active ? "Nonaktifkan" : "Aktifkan"}
                </SmallBtn>
              </div>
            </Card>
          ))}
        </div>
      </PageState>

      {dialog?.mode === "create" && (
        <UserFormDialog onClose={() => setDialog(null)} />
      )}
      {dialog?.mode === "edit" && (
        <UserFormDialog user={dialog.user} onClose={() => setDialog(null)} />
      )}
      {dialog?.mode === "reset" && (
        <ResetDialog user={dialog.user} onClose={() => setDialog(null)} />
      )}
    </div>
  );
}

function Tag({ children, className }: { children: React.ReactNode; className: string }) {
  return (
    <span className={`rounded-md px-2 py-0.5 text-[11px] font-semibold ${className}`}>
      {children}
    </span>
  );
}

function SmallBtn({
  children,
  onClick,
  className = "text-muted",
}: {
  children: React.ReactNode;
  onClick: () => void;
  className?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg border border-line px-2.5 py-1.5 text-xs font-semibold hover:bg-surface ${className}`}
    >
      {children}
    </button>
  );
}

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-line bg-card p-6 shadow-card"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-lg font-extrabold text-ink">{title}</h2>
        {children}
      </div>
    </div>
  );
}

function UserFormDialog({
  user,
  onClose,
}: {
  user?: ManagedUser;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const isEdit = !!user;
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>(user?.role ?? "perawat");
  const [err, setErr] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: async () =>
      isEdit
        ? api.put(`/users/${user!.id}`, { full_name: fullName.trim() })
        : api.post("/users", {
            full_name: fullName.trim(),
            email: email.trim(),
            password,
            role,
          }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
    onError: () => setErr("Gagal menyimpan. Periksa input atau email duplikat."),
  });

  return (
    <Modal title={isEdit ? "Edit Pengguna" : "Tambah Pengguna"} onClose={onClose}>
      <div className="flex flex-col gap-3">
        <input
          className="input"
          placeholder="Nama Lengkap"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
        {!isEdit && (
          <>
            <input
              className="input"
              placeholder="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <input
              className="input"
              placeholder="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <select
              className="input"
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
            >
              <option value="perawat">Perawat</option>
              <option value="dokter">Dokter</option>
              <option value="admin">Admin</option>
            </select>
          </>
        )}
        {err && <p className="text-[13px] text-danger">{err}</p>}
        <div className="mt-1 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-xl px-4 py-2 text-sm font-semibold text-muted">
            Batal
          </button>
          <button
            onClick={() => save.mutate()}
            disabled={save.isPending}
            className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
          >
            {save.isPending && <Spinner className="h-4 w-4" />} Simpan
          </button>
        </div>
      </div>
    </Modal>
  );
}

function ResetDialog({ user, onClose }: { user: ManagedUser; onClose: () => void }) {
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const reset = useMutation({
    mutationFn: async () =>
      api.post(`/users/${user.id}/reset-password`, { new_password: password }),
    onSuccess: onClose,
    onError: () => setErr("Gagal mereset password."),
  });

  return (
    <Modal title={`Reset Password — ${user.full_name}`} onClose={onClose}>
      <div className="flex flex-col gap-3">
        <input
          className="input"
          type="password"
          placeholder="Password baru (min. 6 karakter)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {err && <p className="text-[13px] text-danger">{err}</p>}
        <div className="mt-1 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-xl px-4 py-2 text-sm font-semibold text-muted">
            Batal
          </button>
          <button
            onClick={() => reset.mutate()}
            disabled={password.length < 6 || reset.isPending}
            className="rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
          >
            Reset
          </button>
        </div>
      </div>
    </Modal>
  );
}
