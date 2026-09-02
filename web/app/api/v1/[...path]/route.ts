import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { API_BASE, TOKEN_COOKIE } from "@/lib/config";

// The SSE branch below returns a long-lived stream; this route can never be
// statically evaluated or cached.
export const dynamic = "force-dynamic";

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

  // Server-Sent Events must stream. Buffering the body via arrayBuffer() would
  // wait for a response that never ends, so the chart would simply hang with no
  // error anywhere. Hand the ReadableStream straight to the browser instead;
  // the cookie->Bearer injection above is unchanged, which is the whole reason
  // SSE beats a WebSocket here — no ticket auth, no bypassing this proxy.
  if (upstream.headers.get("content-type")?.includes("text/event-stream")) {
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  }

  // 204/205/304 are "null body status" codes: constructing a Response with a
  // body and one of these throws, which surfaced as a 500 from this proxy even
  // though the upstream call had succeeded. Affects every 204 endpoint —
  // discharge, reset-password, and the delete routes.
  const nullBody =
    upstream.status === 204 || upstream.status === 205 || upstream.status === 304;
  const payload = nullBody ? null : await upstream.arrayBuffer();
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
