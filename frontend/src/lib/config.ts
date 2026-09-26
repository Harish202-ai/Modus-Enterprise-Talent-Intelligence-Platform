// Public API base. NEXT_PUBLIC_* values are inlined at build time.
//
// Two supported modes:
//  - Direct (local dev): set NEXT_PUBLIC_API_URL (e.g. http://localhost:8000) → the
//    browser calls the backend directly.
//  - Proxied (production): leave NEXT_PUBLIC_API_URL empty → the browser calls
//    same-origin "/v1/*" and the Next middleware (src/middleware.ts) forwards them
//    to BACKEND_URL at runtime. This avoids build-time baking and needs no CORS.
export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
