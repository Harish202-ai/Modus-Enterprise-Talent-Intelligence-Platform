"use client";

import { useState } from "react";

import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth, type AuthUser } from "@/lib/auth";
import { rememberWatched, watchedVideo } from "@/lib/orientation";
import type { SiteVideo } from "@/lib/site";

type Props = { video: SiteVideo; onWatched?: () => void };

/** The one explainer video with a simple "mark as watched" (plan v2 Phase 3). Auto-marks when an mp4 plays to the end. */
export default function ExplainerVideo({ video, onWatched }: Props) {
  const { user, setUser } = useAuth();
  const serverWatched = user?.orientation?.video_key === video.key && user.orientation.video_version === video.version;
  const [localWatched, setLocalWatched] = useState(() => {
    const w = watchedVideo();
    return !!w && w.video_key === video.key && w.video_version === video.version;
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const watched = serverWatched || localWatched;

  const markWatched = async () => {
    if (watched || busy) return;
    const record = { video_key: video.key, video_version: video.version };
    setError("");
    if (user?.role === "candidate") {
      setBusy(true);
      try {
        const updated = await apiFetch<AuthUser>("/v1/candidates/me/orientation", { method: "POST", body: JSON.stringify(record) });
        setUser({ ...user, orientation: updated.orientation });
      } catch (err) {
        setError(errorMessage(err));
        setBusy(false);
        return;
      }
      setBusy(false);
    }
    else rememberWatched(record); // not signed in yet: sent with the registration
    setLocalWatched(true);
    onWatched?.();
  };

  return (
    <div>
      <div className="aspect-video w-full overflow-hidden rounded-lg bg-primary">
        {video.provider === "youtube" && video.embed_url ? (
          <iframe
            className="h-full w-full"
            src={video.embed_url}
            title={video.title}
            allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen"
            allowFullScreen
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
          />
        ) : (
          <video className="h-full w-full" controls preload="metadata" onEnded={markWatched} aria-label={video.title}>
            <source src={video.url} />
            {video.captions_url && <track kind="captions" src={video.captions_url} srcLang="en" label="English" default />}
          </video>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        {watched ? (
          <p role="status" className="text-sm font-medium">
            <span aria-hidden className="mr-1 text-accent-cta">
              ✓
            </span>
            Marked as watched
          </p>
        ) : (
          <button
            onClick={markWatched}
            disabled={busy}
            className="rounded-md border border-primary/20 bg-surface-card px-4 py-2 text-sm transition-colors hover:border-accent-cta disabled:opacity-50"
          >
            {busy ? "Saving…" : "Mark as watched"}
          </button>
        )}
        {error && (
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
        )}
      </div>

      {video.transcript && (
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer text-primary/70 underline decoration-accent-cta underline-offset-2">Read the transcript</summary>
          <p className="mt-2 whitespace-pre-line text-primary/80">{video.transcript}</p>
        </details>
      )}
    </div>
  );
}
