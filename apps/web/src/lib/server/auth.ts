// Server-only helpers for the backend-for-frontend: tokens live in httpOnly cookies, never in browser JS.
import { NextResponse } from "next/server";

export const API_URL = process.env.API_URL ?? "http://localhost:8000";
export const ACCESS_COOKIE = "pht_access";
export const REFRESH_COOKIE = "pht_refresh";

export type Tokens = { access_token: string; refresh_token: string; expires_in: number };

// Secure cookies require HTTPS; enable with COOKIE_SECURE=true behind TLS (always do this in production).
const secure = process.env.COOKIE_SECURE === "true";

export function setAuthCookies(res: NextResponse, t: Tokens) {
  const base = { httpOnly: true, sameSite: "lax" as const, secure, path: "/" };
  res.cookies.set(ACCESS_COOKIE, t.access_token, { ...base, maxAge: t.expires_in });
  res.cookies.set(REFRESH_COOKIE, t.refresh_token, { ...base, maxAge: 7 * 24 * 3600 });
}

export function clearAuthCookies(res: NextResponse) {
  res.cookies.delete(ACCESS_COOKIE);
  res.cookies.delete(REFRESH_COOKIE);
}

export async function refreshTokens(refresh: string): Promise<Tokens | null> {
  const r = await apiFetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  return r.ok ? ((await r.json()) as Tokens) : null;
}

/** Pass FastAPI's error body through unchanged so the UI can show `detail`. */
export async function relayError(r: Response) {
  const body = await r.text();
  return new NextResponse(body || JSON.stringify({ detail: r.statusText }), {
    status: r.status,
    headers: { "Content-Type": r.headers.get("content-type") ?? "application/json" },
  });
}

/** fetch() to the API that turns network failures (API down/restarting) into a clean 502 instead of a crash. */
export async function apiFetch(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, { ...init, cache: "no-store" });
  } catch {
    return new Response(JSON.stringify({ detail: "The health record service is unavailable. Please try again shortly." }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}
