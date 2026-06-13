import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { TOKEN_COOKIE } from "@/lib/config";

export async function POST() {
  const jar = await cookies();
  jar.delete(TOKEN_COOKIE);
  return NextResponse.json({ ok: true });
}
