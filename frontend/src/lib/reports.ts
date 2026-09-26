import { apiFetch } from "./api";
import type { CapabilityScore, TalentDnaScore, ValuesScore, AiScore } from "./scores";

export type ReportItem = { label: string; detail: string };
export type SummaryReport = {
  type: "summary";
  readiness: number | null;
  readiness_band: string;
  evidence_confidence: number;
  evidence_coverage: number;
  headline: string;
  strengths: ReportItem[];
  development_themes: ReportItem[];
  has_detailed_report: boolean;
  scored: boolean;
};
export type DetailedReport = SummaryReport & {
  type: "detailed";
  composite: { readiness: number | null; readiness_components: Record<string, number>; evidence_confidence: number; evidence_coverage: number };
  capability: CapabilityScore;
  talent_dna: TalentDnaScore;
  values: ValuesScore;
  written_communication: AiScore;
  case_study: AiScore;
};

export type ExplainerReply = { mode: "why" | "coach"; available: boolean; answer: string };
export type VoiceCapability = { provider: string; stt: string; tts: string; configured: boolean };

export const reportApi = {
  summary: () => apiFetch<{ report: SummaryReport }>("/v1/me/report").then((r) => r.report),
  detailed: () => apiFetch<{ report: DetailedReport }>("/v1/me/report/detailed").then((r) => r.report),
  ask: (question: string, mode: "why" | "coach" = "why") =>
    apiFetch<ExplainerReply>("/v1/me/explainer", { method: "POST", body: JSON.stringify({ question, mode }) }),
  voice: () => apiFetch<VoiceCapability>("/v1/me/voice"),
};
