import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PRODUCTION_HOSTS = new Set(["decantsleo.com", "www.decantsleo.com"]);

/** Hosts distintos al de producción (VPS de pruebas, localhost) no deben indexarse. */
export function middleware(request: NextRequest) {
  const host = (request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? "")
    .split(",")[0]
    .trim()
    .toLowerCase()
    .replace(/:\d+$/, "");
  const response = NextResponse.next();
  if (!PRODUCTION_HOSTS.has(host)) response.headers.set("X-Robots-Tag", "noindex, nofollow");
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|hero/frames).*)"],
};
