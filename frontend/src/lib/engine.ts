import { apiFetch, apiUpload } from "./api";

export type QuestionType = "single_choice" | "multi_select" | "likert" | "rank" | "free_text" | "file_upload";
export type Option = { key: string; label: string };
export type Question = {
  key: string;
  type: QuestionType;
  prompt: string;
  options?: Option[];
  min_selections?: number;
  max_selections?: number;
  min_words?: number;
  max_length?: number;
  upload_kinds?: string[];
  upload_max_mb?: number;
  upload_role?: "none" | "resume";
};
export type Section = {
  key: string;
  title: string;
  instructions?: string | null;
  skip_if: { question_key: string; answer: string }[];
  questions: Question[];
};
export type Definition = { key: string; version: number; name: string; purpose?: string; time_limit_minutes?: number; sections: Section[] };
export type FileAnswer = { file_id: string; filename: string; kind: string; size: number };
export type Answer = string | string[] | FileAnswer;
export type Answers = Record<string, Answer>;
export type Progress = { answered: number; total: number; skipped_sections: string[] };
export type Attempt = {
  id: string;
  assessment_key: string;
  assessment_version: number;
  status: "in_progress" | "submitted";
  answers: Answers;
  current_section_key: string | null;
  started_at: string;
  submitted_at: string | null;
  progress: Progress;
  definition: Definition;
};
export type MyAssessment = {
  key: string;
  name: string;
  status: "not_started" | "in_progress" | "submitted" | "coming_soon";
  attempt_id: string | null;
  progress: Progress | null;
  purpose?: string;
  submitted_at?: string | null;
};

export const engineApi = {
  mine: () => apiFetch<MyAssessment[]>("/v1/me/assessments"),
  start: (code: string) => apiFetch<Attempt>(`/v1/assessments/${encodeURIComponent(code)}/attempts`, { method: "POST" }),
  save: (attemptId: string, answers: Record<string, Answer | null>, currentSectionKey?: string) =>
    apiFetch<{ id: string; updated_at: string; progress: Progress }>(`/v1/attempts/${attemptId}/answers`, {
      method: "PUT",
      body: JSON.stringify({ answers, current_section_key: currentSectionKey ?? null }),
    }),
  submit: (attemptId: string, skipped: string[] = []) =>
    apiFetch<Attempt>(`/v1/attempts/${attemptId}/submit`, { method: "POST", body: JSON.stringify({ skipped }) }),
  upload: (attemptId: string, questionKey: string, file: File) =>
    apiUpload<{ answer: FileAnswer; progress: Progress; resume_claim: { id: string; status: string } | null }>(
      `/v1/attempts/${attemptId}/files?question_key=${encodeURIComponent(questionKey)}`,
      file,
    ),
};

/** Same rule as the server: a section is skipped when any rule matches an earlier answer. */
export function isSkipped(section: Section, answers: Answers): boolean {
  return section.skip_if.some((rule) => {
    const a = answers[rule.question_key];
    return Array.isArray(a) ? a.includes(rule.answer) : typeof a === "string" && a === String(rule.answer);
  });
}

export const isFileAnswer = (a: Answer | undefined): a is FileAnswer => !!a && typeof a === "object" && !Array.isArray(a) && "file_id" in a;

export const wordCount = (text: string) => (text.trim() ? text.trim().split(/\s+/).length : 0);

/** Client-side mirror of the server's completeness check (the server re-checks on submit). */
export function answerProblem(q: Question, a: Answer | undefined): string | null {
  const keys = (q.options ?? []).map((o) => o.key);
  switch (q.type) {
    case "single_choice":
    case "likert":
      return typeof a === "string" && keys.includes(a) ? null : "Choose an answer";
    case "multi_select": {
      const lo = q.min_selections ?? 1;
      const hi = q.max_selections ?? keys.length;
      const n = Array.isArray(a) ? a.length : 0;
      return n >= lo && n <= hi ? null : lo === hi ? `Choose ${lo}` : `Choose ${lo === 1 ? "up to" : `${lo} to`} ${hi}`;
    }
    case "rank":
      return Array.isArray(a) && a.length === keys.length ? null : "Put the statements in order (or confirm the order shown)";
    case "file_upload":
      return isFileAnswer(a) ? null : "Upload a file";
    case "free_text": {
      if (isFileAnswer(a) && q.upload_kinds?.length) return null;
      const text = typeof a === "string" ? a : "";
      if (!text.trim()) return q.upload_kinds?.length ? "Write an answer or upload a file" : "Write an answer";
      if (q.min_words && wordCount(text) < q.min_words) return `Write at least ${q.min_words} words`;
      return null;
    }
  }
}
