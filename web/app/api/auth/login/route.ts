import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { API_BASE, COOKIE_SECURE, TOKEN_COOKIE } from "@/lib/config";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    return NextResponse.json(
      { detail: data?.detail ?? "Email atau password salah" },
      { status: res.status },
    );
  }

  const jar = await cookies();
  jar.set(TOKEN_COOKIE, data.access_token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: COOKIE_SECURE,
    maxAge: 60 * 60 * 8, // 8h
  });

  return NextResponse.json({
    user_id: data.user_id,
    full_name: data.full_name,
    role: data.role,
  });
}
