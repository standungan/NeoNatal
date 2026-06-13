import axios from "axios";

// All data requests go through the same-origin BFF proxy (/api/v1/*),
// which injects the Bearer token server-side from the httpOnly cookie.
export const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

export async function loginRequest(email: string, password: string) {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.detail ?? "Login gagal");
  }
  return res.json();
}

export async function logoutRequest() {
  await fetch("/api/auth/logout", { method: "POST" });
}

export async function fetchMe() {
  const res = await fetch("/api/auth/me", { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}
