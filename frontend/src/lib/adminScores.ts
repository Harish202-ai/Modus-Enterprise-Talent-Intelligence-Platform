import { apiFetch } from "./api";
import type { DimensionScores } from "./scores";

export type QueueResponse = {
  question_key: string;
  prompt?: string | null;
  status: string;
  message?: string;
  scores?: DimensionScores;
  override?: { by: string; reason: string; at: string };
};
export type QueueRow = {
  attempt_id: string;
  assessment_key: string;
  candidate_email: string | null;
  status: string;
  needs_review: boolean;
  model?: string | null;
  computed_at: string;
  responses: QueueResponse[];
};
export type OverrideBody = {
  reasoning_score: number;
  knowledge_score: number;
  communication_score: number;
  overall_confidence: number;
  reason: string;
};

export const adminScoresApi = {
  queue: () => apiFetch<{ queue: QueueRow[] }>("/v1/admin/scores/review").then((r) => r.queue),
  override: (attemptId: string, questionKey: string, body: OverrideBody) =>
    apiFetch<{ result: { responses: QueueResponse[] } }>(
      `/v1/admin/scores/${encodeURIComponent(attemptId)}/responses/${encodeURIComponent(questionKey)}/override`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  approve: (attemptId: string) => apiFetch(`/v1/admin/scores/${encodeURIComponent(attemptId)}/approve`, { method: "POST" }),
};
