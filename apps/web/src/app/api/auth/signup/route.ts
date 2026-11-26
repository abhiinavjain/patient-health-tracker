import { NextRequest, NextResponse } from "next/server";
import { API_URL, apiFetch, relayError, setAuthCookies, type Tokens } from "@/lib/server/auth";

export async function POST(req: NextRequest) {
  const r = await apiFetch(`${API_URL}/api/v1/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: await req.text(),
  });
  if (!r.ok) return relayError(r);
  const tokens = (await r.json()) as Tokens;
  const me = await apiFetch(`${API_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  const res = NextResponse.json(await me.json(), { status: 201 });
  setAuthCookies(res, tokens);
  return res;
}
