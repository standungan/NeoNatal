// Server-side only configuration.
export const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

// httpOnly cookie that holds the FastAPI JWT. Never readable by client JS.
export const TOKEN_COOKIE = "nc_token";

// A `secure` cookie is only sent over HTTPS. Defaults to on in production, but can
// be forced off (COOKIE_SECURE=false) for a plain-HTTP deployment on a bare IP.
// ⚠️ With this off the JWT travels in cleartext — demo only, never for real patient data.
export const COOKIE_SECURE = process.env.COOKIE_SECURE
  ? process.env.COOKIE_SECURE === "true"
  : process.env.NODE_ENV === "production";
