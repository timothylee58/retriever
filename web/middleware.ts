import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  if (path === "/" || path.startsWith("/login")) {
    return NextResponse.next();
  }
  const expected = process.env.DEMO_PASSWORD ?? "retriever-demo";
  if (request.cookies.get("retriever_demo")?.value === expected) {
    return NextResponse.next();
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = { matcher: ["/((?!api|_next|favicon.ico).*)"] };
