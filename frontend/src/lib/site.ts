import { apiFetch } from "./api";

export type SiteVideo = {
  key: string;
  version: number;
  title: string;
  description: string | null;
  provider: "youtube" | "mp4";
  url: string;
  embed_url: string | null;
  captions_url: string | null;
  transcript: string | null;
};

export type TextBlock = { title: string; body: string };

export type LandingPage = {
  key: string;
  version: number;
  headline: string;
  subheadline: string;
  cta_label: string;
  video_heading?: string;
  video_body?: string;
  sections_heading?: string;
  sections?: TextBlock[];
  steps_heading?: string;
  steps?: TextBlock[];
  privacy_note?: string;
  closing_heading?: string;
  closing_body?: string;
  video: SiteVideo | null;
};

/** Public, published site copy (no sign-in needed). */
export const getSitePage = <T = LandingPage>(key: string) => apiFetch<T>(`/v1/site/${encodeURIComponent(key)}`);
