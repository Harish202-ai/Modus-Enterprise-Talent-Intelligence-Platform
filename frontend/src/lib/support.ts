import { apiFetch } from "./api";

export type SupportReply = { answer: string; sources: { key: string; title: string }[]; grounded: boolean; mode?: string };

export const supportApi = {
  // Public — no auth required.
  chat: (question: string) => apiFetch<SupportReply>("/v1/support/chat", { method: "POST", body: JSON.stringify({ question }) }),
};
