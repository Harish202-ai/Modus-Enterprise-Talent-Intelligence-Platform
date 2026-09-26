import { NextResponse, type NextRequest } from "next/server";

/**
 * Runtime API proxy for deployments.
 *
 * In production we DON'T bake NEXT_PUBLIC_API_URL into the build. Instead the
 * browser calls same-origin `/v1/*`, and this middleware forwards those requests
 * to the backend named by the runtime env var BACKEND_URL. Benefits:
 *   - No build-time env baking (the value is read per-request, at runtime).
 *   - Same-origin from the browser's view → no CORS needed, and the httpOnly
 *     refresh cookie is set/sent on the frontend origin.
 *
 * If BACKEND_URL is unset (e.g. local dev, where NEXT_PUBLIC_API_URL points the
 * browser straight at the backend) this does nothing.
 */
// Deployed backend (Railway). Overridable at runtime via the BACKEND_URL env var;
// falls back to this default so the proxy works out of the box after a push.
const DEFAULT_BACKEND = "https://modus-enterprise-talent-intelligence-platform-production.up.railway.app";

export function middleware(req: NextRequest) {
  const backend = (process.env.BACKEND_URL || DEFAULT_BACKEND).replace(/\/$/, "");
  if (!backend) return NextResponse.next();
  const target = new URL(req.nextUrl.pathname + req.nextUrl.search, backend);
  return NextResponse.rewrite(target);
}

export const config = {
  // Proxy only the API namespace; everything else is served by Next as normal.
  matcher: "/v1/:path*",
};
