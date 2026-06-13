import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { API_BASE, TOKEN_COOKIE } from "@/lib/config";

// Back-end-for-front-end proxy: forwards /api/v1/* to FastAPI with the JWT
// (read from the httpOnly cookie) injected as a Bearer header. The token
// never reaches the browser, and same-origin calls avoid CORS entirely.
async function handle(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  const { path } = await ctx.params;
  const jar = await cookies();
  const token = jar.get(TOKEN_COOKIE)?.value;

  const target = `${API_BASE}/api/v1/${path.join("/")}${req.nextUrl.search}`;

  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const contentType = req.headers.get("content-type");
  if (contentType) headers["Content-Type"] = contentType;

  const method = req.method;
  const hasBody = method !== "GET" && method !== "HEAD";
  const bodyBuf = hasBody ? Buffer.from(await req.arrayBuffer()) : undefined;

  const upstream = await fetch(target, {
    method,
    headers,
    body: bodyBuf,
    cache: "no-store",
  });

  const payload = await upstream.arrayBuffer();
  const out = new NextResponse(payload, { status: upstream.status });

  for (const h of ["content-type", "content-disposition"]) {
    const v = upstream.headers.get(h);
    if (v) out.headers.set(h, v);
  }
  return out;
}

export {
  handle as GET,
  handle as POST,
  handle as PUT,
  handle as DELETE,
  handle as PATCH,
};
