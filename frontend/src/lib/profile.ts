import { apiFetch, apiUpload } from "./api";

export type Role = { title: string; organisation?: string | null; start?: string | null; end?: string | null; highlights: string[] };
export type Education = { qualification: string; institution?: string | null; year?: number | null };
export type ResumeProfile = {
  summary?: string | null;
  total_years_experience?: number | null;
  roles: Role[];
  industries: string[];
  skills: string[];
  education: Education[];
};
export type ResumeClaim = {
  id: string;
  status: "processing" | "parsed" | "needs_review" | "unreadable" | "unavailable" | "confirmed";
  message?: string | null;
  evidence_tier: "self_reported";
  file?: { id: string; filename: string; size: number; kind: string } | null;
  parsed?: ResumeProfile | null;
  confirmed?: ResumeProfile | null;
  created_at: string;
  confirmed_at?: string | null;
};

export const EMPTY_PROFILE: ResumeProfile = { summary: "", total_years_experience: null, roles: [], industries: [], skills: [], education: [] };

export const profileApi = {
  get: () => apiFetch<{ claim: ResumeClaim | null }>("/v1/me/resume"),
  upload: (file: File) => apiUpload<ResumeClaim>("/v1/me/resume", file),
  confirm: (id: string, profile: ResumeProfile) => apiFetch<ResumeClaim>(`/v1/me/resume/${id}`, { method: "PUT", body: JSON.stringify(profile) }),
  retry: (id: string) => apiFetch<ResumeClaim>(`/v1/me/resume/${id}/retry`, { method: "POST" }),
};
