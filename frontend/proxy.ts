import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { routes, SESSION_COOKIE } from "@/lib/routes";

/**
 * Route guard. Without a session cookie every page redirects to sign-in, remembering
 * where the visitor was going; with one, the sign-in page redirects into the console.
 * The cookie's validity is checked by the backend on the first API call.
 */
export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const signedIn = request.cookies.has(SESSION_COOKIE);
  const onSignIn = pathname === routes.signIn;

  if (!signedIn && !onSignIn) {
    const signIn = new URL(routes.signIn, request.url);
    if (pathname !== "/") {
      signIn.searchParams.set("redirect", `${pathname}${search}`);
    }
    return NextResponse.redirect(signIn);
  }
  if (signedIn && onSignIn) {
    return NextResponse.redirect(new URL(routes.hostedZones, request.url));
  }
  return NextResponse.next();
}

export const config = {
  // Everything except the API proxy, Next.js internals and static files.
  matcher: ["/((?!api/|_next/|.*\\.[\\w]+$).*)"],
};
