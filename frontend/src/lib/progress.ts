import { apiFetch } from "./api";

export type ProgressRow = { key: string; name: string; before: number | null; after: number | null; delta: number | null };
export type Comparison = {
  assessment_key: string;
  attempts: number;
  status: "not_submitted" | "single" | "compared";
  latest_at?: string | null;
  previous_at?: string | null;
  rows?: ProgressRow[];
};
export type ProgressOverviewRow = { assessment_key: string; attempts: number; can_compare: boolean };

export const progressApi = {
  overview: () => apiFetch<{ progress: ProgressOverviewRow[] }>("/v1/me/progress").then((r) => r.progress),
  compare: (key: string) => apiFetch<Comparison>(`/v1/me/progress/${encodeURIComponent(key)}`),
};
