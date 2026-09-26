import { apiFetch, apiUploadForm } from "./api";

export type InterviewQuestion = { key: string; prompt: string; seconds: number; order: number };
export type InterviewConfig = { questions: InterviewQuestion[]; max_warnings: number };
export type InterviewRecord = {
  id: string;
  file: { id: string; filename: string; kind: string } | null;
  warnings: number;
  auto_submitted: boolean;
  answered: number;
  questions_total: number;
  duration_seconds: number | null;
  created_at: string;
};

export type SubmitMeta = { warnings: number; auto_submitted: boolean; answered: number; duration_seconds: number };

export const interviewApi = {
  config: () => apiFetch<InterviewConfig>("/v1/me/interview"),
  latest: () => apiFetch<{ interview: InterviewRecord | null }>("/v1/me/interview/latest").then((r) => r.interview),
  submit: (blob: Blob, meta: SubmitMeta) => {
    const form = new FormData();
    const ext = blob.type.includes("mp4") ? "mp4" : "webm";
    form.append("file", blob, `interview.${ext}`);
    form.append("warnings", String(meta.warnings));
    form.append("auto_submitted", String(meta.auto_submitted));
    form.append("answered", String(meta.answered));
    form.append("duration_seconds", String(meta.duration_seconds));
    return apiUploadForm<InterviewRecord>("/v1/me/interview", form);
  },
};
