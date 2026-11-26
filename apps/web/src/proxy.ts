// Optimistic route protection (Next 16 "proxy", formerly middleware). Real authorization happens in the API.
import { NextRequest, NextResponse } from "next/server";

const PUBLIC = ["/login", "/signup"];

export function proxy(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  const hasSession = req.cookies.has("pht_access") || req.cookies.has("pht_refresh");
  const isPublic = PUBLIC.some((p) => pathname === p || pathname.startsWith(`${p}/`));

  if (!hasSession && !isPublic) {
    const url = new URL("/login", req.url);
    if (pathname !== "/") url.searchParams.set("next", pathname + search);
    return NextResponse.redirect(url);
  }
  if (hasSession && isPublic) return NextResponse.redirect(new URL("/", req.url));
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|ico|webp)$).*)"],
};
