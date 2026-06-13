// Server-side only configuration.
export const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

// httpOnly cookie that holds the FastAPI JWT. Never readable by client JS.
export const TOKEN_COOKIE = "nc_token";
