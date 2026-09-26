"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Explainer from "@/components/chat/Explainer";
import { ApiError, errorMessage } from "@/lib/api";
import { roadmapApi, type Roadmap } from "@/lib/roadmap";

const card = "rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6";

export default function RoadmapView() {
  const [roadmap, setRoadmap] = useState<Roadmap | undefined>(undefined);
  const [locked, setLocked] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let stop = false;
    roadmapApi
      .mine()
      .then((r) => !stop && setRoadmap(r))
      .catch((err) => {
        if (stop) return;
        if (err instanceof ApiError && err.status === 402) setLocked(true);
        else setError(errorMessage(err));
      });
    return () => {
      stop = true;
    };
  }, []);

  if (locked) {
    return (
      <div className={`${card} reveal text-center`}>
        <h1 className="text-2xl">Development Roadmap</h1>
        <p className="mt-2 text-primary/70">The personalised roadmap is part of the Detailed Report upgrade.</p>
        <Link href="/pricing" className="mt-6 inline-block rounded-md bg-accent-cta px-4 py-2 text-sm font-medium text-primary hover:bg-accent-cta/85">
          Unlock it
        </Link>
      </div>
    );
  }
  if (error) return <p role="alert" className="text-sm text-red-700">{error}</p>;
  if (roadmap === undefined) return <p role="status" className="text-sm text-primary/60">Building your roadmap…</p>;
  if (!roadmap) return <p className="text-sm text-primary/60">Complete a scored assessment to generate your roadmap.</p>;

  return (
    <div className="space-y-8">
      <header className="reveal">
        <h1 className="text-2xl">Your development roadmap</h1>
        {roadmap.reassessment_schedule && <p className="mt-1 text-sm text-primary/60">{roadmap.reassessment_schedule}</p>}
      </header>

      <ol className="relative space-y-4 border-l border-primary/15 pl-6">
        {roadmap.milestones.map((m, i) => (
          <li key={i} className={`reveal reveal-${Math.min(i + 1, 4)} relative`}>
            <span className="absolute -left-[1.9rem] mt-1 flex h-4 w-4 items-center justify-center rounded-full bg-accent-cta text-[10px] text-primary" aria-hidden>
              {m.week}
            </span>
            <div className={card}>
              <div className="flex items-baseline justify-between gap-2">
                <h2 className="text-base">{m.title}</h2>
                <span className="text-xs text-primary/55">Week {m.week}</span>
              </div>
              <p className="mt-1 text-sm text-primary/70">{m.focus}</p>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
                {m.actions.map((a, j) => (
                  <li key={j}>{a}</li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-primary/55">
                Resource · <span className="uppercase tracking-wide">{m.resource.type}</span> — {m.resource.title}
              </p>
            </div>
          </li>
        ))}
      </ol>

      <Explainer mode="coach" />
    </div>
  );
}
