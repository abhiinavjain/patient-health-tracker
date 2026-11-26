import { NextRequest, NextResponse } from "next/server";
import { API_URL, apiFetch, relayError, setAuthCookies, type Tokens } from "@/lib/server/auth";

export async function POST(req: NextRequest) {
  const { email, password } = (await req.json()) as { email?: string; password?: string };
  const form = new URLSearchParams({ username: email ?? "", password: password ?? "" });
  const r = await apiFetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  if (!r.ok) return relayError(r);
  const tokens = (await r.json()) as Tokens;
  const me = await apiFetch(`${API_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  const res = NextResponse.json(await me.json());
  setAuthCookies(res, tokens);
  return res;
}
