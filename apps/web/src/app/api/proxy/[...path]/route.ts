// Forwards /api/proxy/<path> to FastAPI /api/v1/<path>, attaching the access token from the httpOnly cookie.
// Refreshes an expired access token once, transparently, and rotates the cookies.
import { NextRequest, NextResponse } from "next/server";
import {
  ACCESS_COOKIE, API_URL, REFRESH_COOKIE, apiFetch, clearAuthCookies, refreshTokens, setAuthCookies, type Tokens,
} from "@/lib/server/auth";

async function forward(url: string, req: NextRequest, body: string | undefined, token?: string) {
  const headers: Record<string, string> = {};
  const ct = req.headers.get("content-type");
  if (ct) headers["Content-Type"] = ct;
  if (token) headers.Authorization = `Bearer ${token}`;
  return apiFetch(url, { method: req.method, headers, body });
}

async function handler(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const url = `${API_URL}/api/v1/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`;
  const body = req.method === "GET" || req.method === "HEAD" ? undefined : await req.text();

  let access = req.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
  let rotated: Tokens | null = null;
  if (!access && refresh) {
    rotated = await refreshTokens(refresh);
    access = rotated?.access_token;
  }
  let r = await forward(url, req, body, access);
  if (r.status === 401 && refresh && !rotated) {
    rotated = await refreshTokens(refresh);
    if (rotated) r = await forward(url, req, body, rotated.access_token);
  }

  const out = new NextResponse(r.status === 204 ? null : await r.arrayBuffer(), {
    status: r.status,
    headers: { "Content-Type": r.headers.get("content-type") ?? "application/json" },
  });
  if (r.status === 401) clearAuthCookies(out);
  else if (rotated) setAuthCookies(out, rotated);
  return out;
}

export { handler as GET, handler as POST, handler as PATCH, handler as PUT, handler as DELETE };
