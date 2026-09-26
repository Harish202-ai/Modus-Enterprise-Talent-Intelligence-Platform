"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";

import ExplainerVideo from "@/components/ExplainerVideo";
import AIOrb from "@/components/three/AIOrbLazy";
import { ButtonLink } from "@/components/ui/Button";
import { SectionLabel } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { TiltCard } from "@/components/fx/TiltCard";
import { FloatingCard } from "@/components/fx/FloatingCard";
import { ParallaxScene, ParallaxLayer } from "@/components/fx/Parallax";
import { CursorSpotlight } from "@/components/fx/CursorSpotlight";
import { Reveal, RevealGroup, RevealItem } from "@/components/fx/Reveal";
import { Blobs } from "@/components/fx/Blobs";
import { ApiError, errorMessage } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";
import { getSitePage, type LandingPage } from "@/lib/site";

type State = { kind: "loading" } | { kind: "ready"; page: LandingPage } | { kind: "missing" } | { kind: "error"; message: string };

/**
 * Built-in default landing content. Used as a fallback so the landing page ALWAYS
 * renders — even before the backend is reachable or the `site_content` doc is
 * published. When the API returns a published landing, that (admin-edited) content
 * is used instead.
 */
const DEFAULT_LANDING: LandingPage = {
  key: "landing",
  version: 0,
  headline: "Understand your talent. Build what comes next.",
  subheadline:
    "METI uses AI-powered assessments and evidence analysis to understand your professional capabilities, identify development gaps, and map where you can grow next.",
  cta_label: "Create your account",
  sections_heading: "Why enterprise talent intelligence",
  sections: [
    { title: "AI-powered assessment", body: "Adaptive assessments measure reasoning, knowledge and communication — not memorised answers." },
    { title: "Evidence analysis", body: "Your CV and uploaded work are weighed as real evidence, so scores reflect what you can actually do." },
    { title: "Talent intelligence", body: "A clear capability profile, development gaps, career directions and a personalised roadmap." },
  ],
  steps_heading: "How it works",
  steps: [
    { title: "Build your profile", body: "Add your background and upload your CV — read for evidence, not keywords." },
    { title: "Complete your assessment", body: "Answer adaptive questions and submit work samples across capabilities." },
    { title: "AI understands your evidence", body: "MODUS scores your reasoning, knowledge and communication with cited evidence." },
    { title: "Receive your report", body: "Get a talent-intelligence profile, career recommendations and a development roadmap." },
  ],
  closing_heading: "Ready to understand your potential?",
  closing_body: "Build your profile, complete one assessment, and receive your Talent Intelligence report.",
  privacy_note: "Your data is used only to run your assessments and reports. AI-assisted scoring is reviewable by a person.",
  video: null,
};

async function loadLanding(): Promise<State> {
  try {
    return { kind: "ready", page: await getSitePage("landing") };
  } catch (err) {
    // Never leave the landing blank: fall back to built-in default content when the
    // API is unreachable or the landing isn't published yet.
    if (!(err instanceof ApiError && err.status === 404)) console.warn("Landing API unavailable, using default content:", errorMessage(err));
    return { kind: "ready", page: DEFAULT_LANDING };
  }
}

export default function LandingView() {
  const { user } = useAuth();
  const [state, setState] = useState<State>({ kind: "loading" });
  const [justWatched, setJustWatched] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadLanding().then((next) => !cancelled && setState(next));
    return () => {
      cancelled = true;
    };
  }, []);

  const retry = useCallback(async () => {
    setState({ kind: "loading" });
    setState(await loadLanding());
  }, []);

  if (state.kind === "loading") {
    return (
      <div className="mx-auto w-full max-w-3xl animate-pulse space-y-4 px-6 py-24" role="status" aria-label="Loading">
        <div className="h-12 w-4/5 rounded-2xl bg-ink/8" />
        <div className="h-5 w-3/5 rounded bg-ink/8" />
        <div className="h-12 w-44 rounded-full bg-ink/8" />
      </div>
    );
  }
  if (state.kind === "error") {
    return (
      <div role="alert" className="mx-auto max-w-md px-6 py-24 text-center">
        <h1 className="font-heading text-2xl font-extrabold">We couldn’t load this page</h1>
        <p className="mt-2 text-sm text-muted">{state.message}</p>
        <button onClick={retry} className="mt-6 inline-flex h-11 items-center rounded-full border border-line bg-card px-5 text-sm font-semibold text-ink shadow-[var(--shadow-soft)] transition-colors hover:border-violet/40">Try again</button>
      </div>
    );
  }
  if (state.kind === "missing") {
    return (
      <div className="mx-auto max-w-md px-6 py-24 text-center">
        <h1 className="font-heading text-2xl font-extrabold">METI-MC</h1>
        <p className="mt-2 text-sm text-muted">The landing page hasn’t been published yet.</p>
        <div className="mt-6 flex justify-center gap-3">
          <ButtonLink href="/register" size="md">Create account</ButtonLink>
          <ButtonLink href="/login" variant="secondary" size="md">Sign in</ButtonLink>
        </div>
      </div>
    );
  }

  const { page } = state;
  const next = user ? { href: homeFor(user), label: "Go to your account" } : { href: "/register", label: page.cta_label };

  return (
    <div className="w-full">
      {/* ── Hero ─────────────────────────────────────────────── */}
      <section className="relative overflow-hidden px-4 pb-16 pt-10 md:pt-14">
        <Blobs />
        <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-[1.05fr_1fr]">
          <div className="relative">
            <CursorSpotlight />
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
              <SectionLabel><Icon name="spark" size={14} /> AI-Powered Talent Intelligence</SectionLabel>
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.05 }}
              className="mt-5 font-heading text-[40px] font-extrabold leading-[1.04] tracking-tight text-ink md:text-[60px]"
            >
              {page.headline}
            </motion.h1>
            <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.12 }} className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
              {page.subheadline}
            </motion.p>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.19 }} className="mt-8 flex flex-wrap items-center gap-3">
              <ButtonLink href={next.href} size="lg">{next.label} <Icon name="arrow" size={18} /></ButtonLink>
              {page.video && (
                <a href="#explainer" className="inline-flex h-13 items-center gap-2 rounded-full border border-line bg-card px-7 py-3.5 text-base font-semibold text-ink shadow-[var(--shadow-soft)] transition-colors hover:border-violet/40">
                  <Icon name="play" size={16} /> {page.video_heading || "Watch the explainer"}
                </a>
              )}
            </motion.div>
          </div>

          {/* Hero visual — AI orb + parallax floating cards */}
          <ParallaxScene className="relative mx-auto h-[420px] w-full max-w-[500px] md:h-[500px]">
            <ParallaxLayer depth={0.25} className="absolute inset-0">
              <div className="absolute left-1/2 top-1/2 h-[320px] w-[320px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(123,110,246,0.25),transparent_70%)] blur-2xl" />
            </ParallaxLayer>
            <ParallaxLayer depth={1} className="absolute inset-0">
              <AIOrb className="h-full w-full" />
            </ParallaxLayer>
            <ParallaxLayer depth={1.5} className="absolute left-2 top-10">
              <FloatingCard delay={0.4}>
                <div className="flex items-center gap-2.5">
                  <span className="grid h-8 w-8 place-items-center rounded-lg bg-violet/15 text-violet"><Icon name="brain" size={16} /></span>
                  <div><div className="text-xs font-semibold text-ink">Talent Intelligence</div><div className="text-[11px] text-muted">Evidence-based</div></div>
                </div>
              </FloatingCard>
            </ParallaxLayer>
            <ParallaxLayer depth={1.7} className="absolute right-0 top-24">
              <FloatingCard delay={0.6}>
                <div className="text-[11px] font-medium text-muted">Readiness</div>
                <div className="font-heading text-2xl font-extrabold text-gradient">Strong</div>
              </FloatingCard>
            </ParallaxLayer>
            <ParallaxLayer depth={1.3} className="absolute bottom-24 left-0">
              <FloatingCard delay={0.75}>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-mint-500" />
                  <span className="text-xs font-semibold text-ink">Values profile</span>
                  <span className="rounded-full bg-mint-500/15 px-2 py-0.5 text-[10px] font-bold text-[#159c7a]">Mapped</span>
                </div>
              </FloatingCard>
            </ParallaxLayer>
            <ParallaxLayer depth={0.8} className="absolute right-16 top-0">
              <FloatingCard delay={0.5} float={false} className="!px-3 !py-2">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-violet-ink"><Icon name="spark" size={12} /> AI Analysis</div>
              </FloatingCard>
            </ParallaxLayer>
          </ParallaxScene>
        </div>
      </section>

      {/* ── Explainer video (unchanged data) ─────────────────── */}
      {page.video && (
        <section id="explainer" className="scroll-mt-24 px-4 pb-20">
          <Reveal className="mx-auto max-w-3xl">
            <div className="rounded-3xl border border-line bg-card p-6 shadow-[var(--shadow-soft)] sm:p-8">
              <SectionLabel><Icon name="play" size={13} /> Watch</SectionLabel>
              <h2 className="mt-3 font-heading text-2xl font-extrabold text-ink">{page.video_heading || page.video.title}</h2>
              {page.video_body && <p className="mt-2 text-muted">{page.video_body}</p>}
              <div className="mt-6 overflow-hidden rounded-2xl">
                <ExplainerVideo video={page.video} onWatched={() => setJustWatched(true)} />
              </div>
              {justWatched && !user && (
                <div className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-[linear-gradient(120deg,#f4f1ff,#eef6ff)] p-4">
                  <p className="text-sm font-medium text-ink">Great — you’re ready for the next step.</p>
                  <ButtonLink href="/register" size="sm">{page.cta_label}</ButtonLink>
                </div>
              )}
            </div>
          </Reveal>
        </section>
      )}

      {/* ── Why (sections) as tilt cards ─────────────────────── */}
      {!!page.sections?.length && (
        <section className="px-4 py-16">
          <div className="mx-auto max-w-6xl">
            {page.sections_heading && (
              <Reveal className="mx-auto max-w-2xl text-center">
                <h2 className="font-heading text-3xl font-extrabold text-ink md:text-[40px]">{page.sections_heading}</h2>
              </Reveal>
            )}
            <RevealGroup className="mt-10 grid gap-5 md:grid-cols-3">
              {page.sections.map((s, i) => (
                <RevealItem key={s.title}>
                  <TiltCard className="h-full rounded-3xl">
                    <article className="flex h-full flex-col rounded-3xl border border-line bg-card p-6 shadow-[var(--shadow-soft)]">
                      <span className="grid h-11 w-11 place-items-center rounded-2xl bg-violet/12 text-violet"><Icon name={["brain", "shield", "career"][i % 3]} /></span>
                      <h3 className="mt-4 text-lg font-bold text-ink">{s.title}</h3>
                      <p className="mt-2 text-sm leading-relaxed text-muted">{s.body}</p>
                    </article>
                  </TiltCard>
                </RevealItem>
              ))}
            </RevealGroup>
          </div>
        </section>
      )}

      {/* ── Journey (steps) as timeline ──────────────────────── */}
      {!!page.steps?.length && (
        <section className="px-4 py-16">
          <div className="mx-auto max-w-3xl">
            {page.steps_heading && (
              <Reveal className="text-center">
                <h2 className="font-heading text-3xl font-extrabold text-ink md:text-[40px]">{page.steps_heading}</h2>
              </Reveal>
            )}
            <div className="relative mt-10">
              <div className="absolute bottom-4 left-[22px] top-4 w-0.5 bg-gradient-to-b from-violet via-blue to-mint-500/40" />
              <RevealGroup className="space-y-4">
                {page.steps.map((s, i) => (
                  <RevealItem key={s.title}>
                    <div className="relative flex gap-5">
                      <span className="relative z-10 grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[linear-gradient(135deg,#7b6ef6,#4f9cff)] font-heading text-sm font-extrabold text-white shadow-[var(--shadow-soft)]">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <div className="flex-1 rounded-3xl border border-line bg-card p-5 shadow-[var(--shadow-soft)]">
                        <h3 className="text-lg font-bold text-ink">{s.title}</h3>
                        <p className="mt-1 text-sm leading-relaxed text-muted">{s.body}</p>
                      </div>
                    </div>
                  </RevealItem>
                ))}
              </RevealGroup>
            </div>
          </div>
        </section>
      )}

      {/* ── Closing CTA ──────────────────────────────────────── */}
      <section className="px-4 py-20">
        <Reveal className="mx-auto max-w-4xl">
          <div className="relative overflow-hidden rounded-[2.5rem] bg-[#14121f] px-8 py-16 text-center shadow-[var(--shadow-lift)] md:px-16">
            <div className="pointer-events-none absolute -left-20 -top-20 h-72 w-72 rounded-full bg-violet/40 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-24 -right-16 h-72 w-72 rounded-full bg-blue/30 blur-3xl" />
            <div className="relative">
              {page.closing_heading && <h2 className="font-heading text-3xl font-extrabold text-white md:text-5xl">{page.closing_heading}</h2>}
              {page.closing_body && <p className="mx-auto mt-4 max-w-lg text-white/70">{page.closing_body}</p>}
              <div className="mt-8 flex justify-center">
                <ButtonLink href={next.href} size="lg">{next.label} <Icon name="arrow" size={18} /></ButtonLink>
              </div>
              {page.privacy_note && <p className="mx-auto mt-10 max-w-xl text-xs leading-relaxed text-white/45">{page.privacy_note}</p>}
            </div>
          </div>
        </Reveal>
      </section>
    </div>
  );
}
