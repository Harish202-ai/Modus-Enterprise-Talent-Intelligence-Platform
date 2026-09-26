// Public runtime config. NEXT_PUBLIC_* values are inlined at build time.
export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

if (!API_BASE_URL && typeof window !== "undefined") {
  console.error("NEXT_PUBLIC_API_URL is not set — copy frontend/.env.example to frontend/.env.local");
}
