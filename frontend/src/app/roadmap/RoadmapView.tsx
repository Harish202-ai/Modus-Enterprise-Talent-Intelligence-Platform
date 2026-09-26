"use client";

import { useEffect, useState } from "react";

import Explainer from "@/components/chat/Explainer";
import { ApiError, errorMessage } from "@/lib/api";
import { roadmapApi, type Roadmap } from "@/lib/roadmap";
import { ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { SectionLabel } from "@/components/ui/Card";
import { TiltCard } from "@/components/fx/TiltCard";

const card = "rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6";

/** General development tips — always useful, shown when the personalised roadmap isn't available. */
const TIPS = [
  { icon: "target", a: "violet", title: "Structure before you solve", body: "Break every problem into an issue tree with MECE branches — clarity of structure beats speed of answer." },
  { icon: "reports", a: "blue", title: "Write the answer first", body: "Practice the one-page executive memo: lead with your recommendation, then support it. This is the #1 lever on your Communication score." },
  { icon: "case", a: "mint", title: "Practise on real cases", body: "Work one full case study a week. Time-box it, then compare your reasoning to a strong exemplar." },
  { icon: "chart", a: "amber", title: "Turn data into a story", body: "For every chart, write the ‘so what’ in one sentence before you present it. Data storytelling is the most common development gap." },
  { icon: "chat", a: "pink", title: "Get feedback on your reasoning", body: "Ask a peer to critique how you got to the answer, not just the answer. Reasoning quality compounds fastest." },
  { icon: "evaluations", a: "violet", title: "Reassess and track growth", body: "Retake an assessment after a few weeks of practice — measured progress is the strongest signal of readiness." },
] as const;
const soft: Record<string, string> = { violet: "bg-violet/12 text-violet", blue: "bg-blue/12 text-blue", mint: "bg-mint-500/15 text-[#159c7a]", pink: "bg-pink/15 text-[#d64f8f]", amber: "bg-amber/20 text-[#c9762f]" };

function KnowledgeTips({ heading, sub, cta }: { heading: string; sub: string; cta?: boolean }) {
  return (
    <div className="space-y-6">
      <div className="reveal">
        <SectionLabel><Icon name="spark" size={13} /> Tips to grow</SectionLabel>
        <h1 className="mt-3 font-heading text-3xl font-extrabold text-ink">{heading}</h1>
        <p className="mt-2 max-w-2xl text-muted">{sub}</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {TIPS.map((t) => (
          <TiltCard key={t.title} className="h-full rounded-3xl">
            <div className={`${card} h-full`}>
              <span className={`grid h-11 w-11 place-items-center rounded-2xl ${soft[t.a]}`}><Icon name={t.icon} size={20} /></span>
              <h2 className="mt-4 text-base font-bold text-ink">{t.title}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{t.body}</p>
            </div>
          </TiltCard>
        ))}
      </div>
      {cta && (
        <div className="flex flex-col items-start gap-4 rounded-3xl border border-line bg-[linear-gradient(120deg,#f4f1ff,#eef6ff)] p-7 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-heading text-lg font-extrabold text-ink">Want a roadmap built for you?</h3>
            <p className="text-sm text-muted">The Detailed Report upgrade generates a personalised, milestone-by-milestone plan from your own results.</p>
          </div>
          <ButtonLink href="/pricing" size="md">Unlock your roadmap <Icon name="arrow" size={16} /></ButtonLink>
        </div>
      )}
    </div>
  );
}

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
    return <KnowledgeTips heading="Grow your consulting capability" sub="Your personalised roadmap is part of the Detailed Report upgrade — meanwhile, here are proven ways to sharpen the capabilities MODUS measures." cta />;
  }
  if (error) return <p role="alert" className="text-sm text-red-700">{error}</p>;
  if (roadmap === undefined) return <p role="status" className="text-sm text-muted">Building your roadmap…</p>;
  if (!roadmap) {
    return <KnowledgeTips heading="Start building your roadmap" sub="Complete a scored assessment and MODUS will generate your personalised plan. Until then, these habits improve every capability we assess." />;
  }

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
