import { NextResponse } from "next/server";
import { clearAuthCookies } from "@/lib/server/auth";

export async function POST() {
  const res = new NextResponse(null, { status: 204 });
  clearAuthCookies(res);
  return res;
}
