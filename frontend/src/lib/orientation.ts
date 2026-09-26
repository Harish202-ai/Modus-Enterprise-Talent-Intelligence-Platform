/**
 * "Mark as watched" before sign-up is remembered in this browser only, then sent with the registration
 * (the backend stores it on the account). Storage can be unavailable (private mode) — that's fine.
 */
export type WatchedVideo = { video_key: string; video_version: number };

const KEY = "meti.orientation";

export function rememberWatched(video: WatchedVideo): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(video));
  } catch {
    // storage blocked — the candidate can still mark it from their account later
  }
}

export function watchedVideo(): WatchedVideo | null {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return parsed && typeof parsed.video_key === "string" && Number.isInteger(parsed.video_version) ? parsed : null;
  } catch {
    return null;
  }
}

export function forgetWatched(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}
