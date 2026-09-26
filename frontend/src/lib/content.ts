import { apiFetch, apiUpload } from "./api";

const BASE = "/v1/admin/content";

export type FieldKind = "text" | "textarea" | "number" | "integer" | "bool" | "select" | "tags" | "ref" | "refs" | "json";

export type FieldSpec = {
  name: string;
  label: string;
  kind: FieldKind;
  required: boolean;
  help: string;
  options: string[];
  ref_type: string | null;
  min: number | null;
  max: number | null;
  default: unknown;
};

export type ContentTypeSpec = {
  name: string;
  label: string;
  title_field: string;
  key_help: string;
  fields: FieldSpec[];
};

export type ContentRow = {
  key: string;
  title: unknown;
  latest_version: number;
  latest_status: "draft" | "published";
  published_version: number | null;
  has_draft: boolean;
  updated_at: string;
};

export type ContentVersion = {
  id: string;
  key: string;
  content_type: string;
  version: number;
  status: "draft" | "published";
  data: Record<string, unknown>;
  ref_versions: Record<string, Record<string, number>>;
  based_on_version: number | null;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
  published_at: string | null;
  published_by: string | null;
};

export type ValidationError = { field: string; message: string };

const path = (type: string, key?: string, rest = "") =>
  `${BASE}/${encodeURIComponent(type)}${key ? `/${encodeURIComponent(key)}` : ""}${rest}`;

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const contentApi = {
  types: () => apiFetch<ContentTypeSpec[]>(`${BASE}/types`),
  list: (type: string, status?: "draft" | "published") =>
    apiFetch<ContentRow[]>(path(type) + (status ? `?status=${status}` : "")),
  history: (type: string, key: string) =>
    apiFetch<{ key: string; versions: ContentVersion[] }>(path(type, key)),
  create: (type: string, key: string, data: Record<string, unknown>) =>
    apiFetch<ContentVersion>(path(type), json("POST", { key, data })),
  saveDraft: (type: string, key: string, data: Record<string, unknown>) =>
    apiFetch<ContentVersion>(path(type, key, "/draft"), json("PUT", { data })),
  newVersion: (type: string, key: string) => apiFetch<ContentVersion>(path(type, key, "/draft"), json("POST")),
  discardDraft: (type: string, key: string) => apiFetch<ContentVersion>(path(type, key, "/draft"), json("DELETE")),
  validate: (type: string, key: string) =>
    apiFetch<{ ok: boolean; errors: ValidationError[] }>(path(type, key, "/validate"), json("POST")),
  publish: (type: string, key: string) => apiFetch<ContentVersion>(path(type, key, "/publish"), json("POST")),
  generate: (type: string, instruction: string, existing?: Record<string, unknown>) =>
    apiFetch<{ data: Record<string, unknown> }>(path(type, "generate"), json("POST", { instruction, existing })),
  importFile: (type: string, file: File) => apiUpload<{ created: string[]; skipped: string[]; errors: { index: number; key?: string; message: string }[] }>(path(type, "import"), file),
};

/** Pull a readable message (+ field errors) out of an ApiError body. */
export function describeError(err: unknown): { message: string; errors: ValidationError[] } {
  const body = (err as { body?: unknown })?.body as
    | { detail?: unknown; errors?: ValidationError[] }
    | null
    | undefined;
  if (body && typeof body === "object") {
    if (typeof body.detail === "string") return { message: body.detail, errors: body.errors ?? [] };
    if (Array.isArray(body.detail)) {
      // FastAPI request validation errors.
      const errors = body.detail.map((d: { loc?: unknown[]; msg?: string }) => ({
        field: String(d.loc?.at(-1) ?? "request"),
        message: d.msg ?? "invalid",
      }));
      return { message: "Request was rejected", errors };
    }
  }
  return { message: err instanceof Error ? err.message : "Request failed", errors: [] };
}
