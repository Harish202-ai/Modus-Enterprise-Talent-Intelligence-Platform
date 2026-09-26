import { apiFetch } from "./api";

export type Milestone = {
  week: number;
  title: string;
  focus: string;
  actions: string[];
  resource: { type: string; title: string };
};
export type Roadmap = {
  readiness: number | null;
  milestones: Milestone[];
  reassessment_schedule: string | null;
  generated_at: string;
} | null;

export const roadmapApi = {
  mine: () => apiFetch<{ roadmap: Roadmap }>("/v1/me/roadmap").then((r) => r.roadmap),
  regenerate: () => apiFetch<{ roadmap: Roadmap }>("/v1/me/roadmap/regenerate", { method: "POST" }).then((r) => r.roadmap),
};
