import { apiFetch } from "./api";

export type TalentDimension = { key: string; label: string; raw: number; normalized: number; items: number };
export type BasicValue = { key: string; name: string; raw_mean: number; centered: number };
export type HigherOrderValue = { key: string; name: string; centered: number };
export type Competency = { key: string; name: string; items: number; weighted_pct: number };

type NotSubmitted = { status: "not_submitted" };
type Scored = { status: "scored"; attempt_id: string; assessment_key: string; submitted_at: string | null; computed_at: string };

export type TalentDnaScore = NotSubmitted | (Scored & { dimensions: TalentDimension[]; scored_items: number });
export type ValuesScore =
  | NotSubmitted
  | (Scored & { mrat: number; answered: number; basic: BasicValue[]; higher_order: HigherOrderValue[]; top_values: string[] });
export type CapabilityScore =
  | NotSubmitted
  | (Scored & { correct: number; total: number; overall_pct: number; competencies: Competency[] });

// AI-scored responses (Phase 7): the three named dimensions with cited evidence.
export type DimensionScores = {
  reasoning_score: number;
  reasoning_evidence: string;
  knowledge_score: number;
  knowledge_evidence: string;
  communication_score: number;
  communication_evidence: string;
  overall_confidence: number;
};
export type AiResponse = {
  question_key: string;
  prompt?: string | null;
  status: "scored" | "needs_review" | "pending" | "needs_transcript" | "empty";
  message?: string;
  scores?: DimensionScores;
  rubric_key?: string;
};
export type AiAreaStatus = "not_submitted" | "pending" | "scored" | "partial" | "needs_review" | "needs_transcript" | "empty";
export type AiScore =
  | NotSubmitted
  | { status: Exclude<AiAreaStatus, "not_submitted">; attempt_id: string; submitted_at: string | null; computed_at?: string; model?: string | null; responses?: AiResponse[] };

export type Scores = {
  talent_dna: TalentDnaScore;
  values: ValuesScore;
  capability: CapabilityScore;
  written_communication: AiScore;
  case_study: AiScore;
};

export const DIMENSIONS = [
  { key: "reasoning", label: "Reasoning" },
  { key: "knowledge", label: "Knowledge" },
  { key: "communication", label: "Communication" },
] as const;

export const scoresApi = {
  mine: () => apiFetch<{ scores: Scores }>("/v1/me/scores").then((r) => r.scores),
  rescore: (assessmentKey: string) => apiFetch<AiScore>(`/v1/me/scores/${encodeURIComponent(assessmentKey)}/rescore`, { method: "POST" }),
};

export const isScored = <T extends { status: string }>(s: T): s is Extract<T, { status: "scored" }> => s.status === "scored";
