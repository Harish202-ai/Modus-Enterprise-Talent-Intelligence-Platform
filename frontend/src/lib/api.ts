import { API_BASE_URL } from "./config";

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(`API ${status}`);
  }
}

// The access token lives in memory only; the refresh token is an httpOnly cookie the browser sends to /v1/auth.
let accessToken: string | null = null;
let refreshHandler: (() => Promise<string | null>) | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

/** Registered by the AuthProvider: renews the access token, or returns null when the session is over. */
export function setRefreshHandler(handler: (() => Promise<string | null>) | null) {
  refreshHandler = handler;
}

/**
 * Fetch JSON from the backend. Sends the access token, and on a 401 renews it once and retries.
 * Non-2xx responses throw ApiError with the parsed body.
 */
export async function apiFetch<T>(path: string, init?: RequestInit, retried = false): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init?.headers,
    },
  });
  if (res.status === 401 && !retried && refreshHandler && !path.startsWith("/v1/auth/")) {
    const renewed = await refreshHandler();
    if (renewed) return apiFetch<T>(path, init, true);
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

/** Multipart upload (one file under the field name "file"), with the same auth + one-time token renewal. */
export async function apiUpload<T>(path: string, file: File, retried = false): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: form,
    credentials: "include",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
  if (res.status === 401 && !retried && refreshHandler && (await refreshHandler())) return apiUpload<T>(path, file, true);
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

/** Multipart POST of a prebuilt FormData (file + extra fields), with auth + one-time token renewal. */
export async function apiUploadForm<T>(path: string, form: FormData, retried = false): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: form,
    credentials: "include",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
  if (res.status === 401 && !retried && refreshHandler && (await refreshHandler())) return apiUploadForm<T>(path, form, true);
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

/** Fetch a protected file (with the auth header) and return an object URL — for <video>/<img>/download,
 *  which can't send an Authorization header themselves. Caller should URL.revokeObjectURL when done. */
export async function fetchBlobUrl(path: string, retried = false): Promise<string> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
  if (res.status === 401 && !retried && refreshHandler && (await refreshHandler())) return fetchBlobUrl(path, true);
  if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => null));
  return URL.createObjectURL(await res.blob());
}

/** Human-readable message from any thrown API error. */
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const detail = (err.body as { detail?: unknown } | null)?.detail;
    const fieldErrors = (err.body as { errors?: { message?: string }[] } | null)?.errors;
    if (typeof detail === "string" && fieldErrors?.length === 1 && fieldErrors[0].message) return `${detail}: ${fieldErrors[0].message}`;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg).replace(/^Value error, /, "");
    return `Request failed (HTTP ${err.status})`;
  }
  return err instanceof Error && err.message !== "Failed to fetch" ? err.message : "Cannot reach the server — check your connection";
}

export type HealthResponse = {
  status: "ok" | "degraded";
  service: string;
  environment: string;
  checks: Record<string, "up" | "down">;
};
