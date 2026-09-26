import { apiFetch } from "./api";
import type { Scores } from "./scores";

export type CandidateRow = {
  id: string;
  email: string;
  full_name: string | null;
  status: string;
  created_at: string;
  last_login_at: string | null;
  submitted_assessments: number;
  readiness: number | null;
  readiness_band: string | null;
};

export type ResumeProfile = {
  summary?: string | null;
  total_years_experience?: number | null;
  roles?: { title: string; organisation?: string | null; start?: string | null; end?: string | null; highlights?: string[] }[];
  industries?: string[];
  skills?: string[];
  education?: { qualification: string; institution?: string | null; year?: number | null }[];
};

export type CandidateFile = {
  id: string;
  filename: string;
  kind: string;
  size: number;
  purpose?: string;
  created_at?: string;
};

export type CandidateDetail = {
  user: { id: string; email: string; full_name: string | null; status: string; created_at: string; last_login_at: string | null };
  entitlements: string[];
  attempts: { id: string; assessment_key: string; status: string; submitted_at: string | null; started_at: string | null }[];
  scores: Scores;
  report: { readiness: number | null; readiness_band: string; evidence_confidence: number; strengths: { label: string; detail: string }[]; development_themes: { label: string; detail: string }[]; scored: boolean } | null;
  resume: {
    status: string;
    confirmed?: ResumeProfile | null;
    parsed?: ResumeProfile | null;
    file?: { id: string; filename: string; kind: string } | null;
  } | null;
  interviews: { id: string; file: { id: string; filename: string; kind: string } | null; warnings: number; auto_submitted: boolean; answered: number; questions_total: number; duration_seconds: number | null; created_at: string }[];
  files: CandidateFile[];
};

export const adminUsersApi = {
  list: () => apiFetch<{ candidates: CandidateRow[] }>("/v1/admin/candidates").then((r) => r.candidates),
  detail: (id: string) => apiFetch<CandidateDetail>(`/v1/admin/candidates/${encodeURIComponent(id)}`),
};
