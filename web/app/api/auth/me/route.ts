import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { API_BASE, TOKEN_COOKIE } from "@/lib/config";

export async function GET() {
  const jar = await cookies();
  const token = jar.get(TOKEN_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "unauthenticated" }, { status: 401 });
  }

  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!res.ok) {
    return NextResponse.json({ detail: "unauthenticated" }, { status: 401 });
  }

  return NextResponse.json(await res.json());
}
