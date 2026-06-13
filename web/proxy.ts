import { NextRequest, NextResponse } from "next/server";
import { TOKEN_COOKIE } from "@/lib/config";

interface Claims {
  sub?: string;
  role?: string;
  exp?: number;
}

// Lightweight, unverified decode — used only for UX route-gating.
// Real authorization is always enforced by FastAPI on every request.
function decodeJwt(token: string): Claims | null {
  try {
    const payload = token.split(".")[1];
    const json = Buffer.from(payload, "base64").toString("utf8");
    return JSON.parse(json) as Claims;
  } catch {
    return null;
  }
}

export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const token = req.cookies.get(TOKEN_COOKIE)?.value;
  const claims = token ? decodeJwt(token) : null;
  const valid = !!claims && (!claims.exp || claims.exp * 1000 > Date.now());

  if (pathname === "/login") {
    return valid
      ? NextResponse.redirect(new URL("/dashboard", req.url))
      : NextResponse.next();
  }

  if (!valid) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  if (pathname.startsWith("/admin") && claims?.role !== "admin") {
    return NextResponse.redirect(new URL("/dashboard", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
