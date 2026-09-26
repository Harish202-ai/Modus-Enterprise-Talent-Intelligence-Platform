"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { errorMessage } from "@/lib/api";
import { engineApi, type MyAssessment } from "@/lib/engine";
import { interviewApi, type InterviewRecord } from "@/lib/interview";

const cta = "rounded-md bg-accent-cta px-4 py-2 text-sm font-medium text-primary transition-colors hover:bg-accent-cta/85";
const stepCard = "flex flex-wrap items-center gap-4 rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-5";

export default function AssessmentsHome() {
  const [rows, setRows] = useState<MyAssessment[] | null>(null);
  const [interview, setInterview] = useState<InterviewRecord | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stop = false;
    engineApi
      .mine()
      .then((r) => !stop && setRows(r))
      .catch((err) => !stop && setError(errorMessage(err)));
    interviewApi
      .latest()
      .then((i) => !stop && setInterview(i))
      .catch(() => {});
    return () => {
      stop = true;
    };
  }, []);

  if (error) return <p role="alert" className="text-sm text-red-700">{error}</p>;
  if (!rows) return <p role="status" className="text-sm text-primary/60">Loading your assessments…</p>;

  if (rows.length === 0) {
    return (
      <div>
        <h1 className="text-2xl">Your assessment</h1>
        <div className="mt-6 rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-8 text-center">
          <p className="text-primary/70">You haven’t chosen an assessment package yet.</p>
          <Link href="/pricing" className={`${cta} mt-6 inline-block`}>
            Choose your package
          </Link>
        </div>
      </div>
    );
  }

  const done = rows.filter((r) => r.status === "submitted").length;
  const hasInterview = rows.some((r) => r.key === "written_communication"); // interview ships with the consulting package
  const anySubmitted = done > 0 || !!interview;

  return (
    <div>
      <h1 className="text-2xl">Your assessment</h1>
      <p className="mt-1 text-sm text-primary/60">
        Complete each step below — in any order. Your progress saves automatically, so you can stop and continue on any device. When you&apos;re
        done, your results and report appear at the bottom.
      </p>

      {/* Step 1 — CV profile */}
      <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-primary/50">1 · Your profile</h2>
      <Link href="/profile" className={`${stepCard} mt-2 transition-colors hover:border-accent-cta`}>
        <span className="min-w-0 flex-1">
          <span className="font-heading font-semibold">Your CV profile</span>
          <span className="block text-xs text-primary/60">Upload your CV and check what we understood from it.</span>
        </span>
        <span aria-hidden className="text-accent-cta">→</span>
      </Link>

      {/* Step 2 — the exams in your package */}
      <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-primary/50">
        2 · Your exams <span className="font-normal normal-case text-primary/45">({done} of {rows.length} done)</span>
      </h2>
      <ul className="mt-2 space-y-3">
        {rows.map((r) => {
          const pct = r.progress?.total ? Math.round((r.progress.answered / r.progress.total) * 100) : 0;
          return (
            <li key={r.key} className={stepCard}>
              <div className="min-w-0 flex-1">
                <h3 className="text-base">{r.name}</h3>
                <p className="mt-0.5 text-xs text-primary/60">
                  {r.status === "submitted" && `Submitted ${r.submitted_at ? new Date(r.submitted_at).toLocaleDateString() : ""}`}
                  {r.status === "in_progress" && `In progress · ${pct}%`}
                  {r.status === "not_started" && "Not started"}
                  {r.status === "coming_soon" && "Coming soon"}
                </p>
                {r.status === "in_progress" && (
                  <div className="mt-2 h-1 w-full max-w-xs overflow-hidden rounded-full bg-primary/10">
                    <div className="h-full bg-accent-cta" style={{ width: `${pct}%` }} />
                  </div>
                )}
              </div>
              {r.status === "submitted" ? (
                <span className="text-sm font-medium"><span className="mr-1 text-accent-cta">✓</span>Done</span>
              ) : r.status === "coming_soon" ? null : (
                <Link href={`/assessments/${r.key}`} className={cta}>
                  {r.status === "in_progress" ? "Continue" : "Start"}
                </Link>
              )}
            </li>
          );
        })}
      </ul>

      {/* Step 3 — AI video interview (part of the consulting package) */}
      {hasInterview && (
        <>
          <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-primary/50">3 · AI video interview</h2>
          <div className={`${stepCard} mt-2`}>
            <div className="min-w-0 flex-1">
              <h3 className="text-base">AI video interview</h3>
              <p className="mt-0.5 text-xs text-primary/60">
                {interview
                  ? `Recorded ${new Date(interview.created_at).toLocaleDateString()} · ${interview.answered}/${interview.questions_total} questions${interview.auto_submitted ? " · auto-submitted" : ""}`
                  : "Timed questions on camera. Use a laptop/desktop in Chrome and allow camera + microphone."}
              </p>
            </div>
            {interview ? (
              <Link href="/interview" className="rounded-md border border-primary/20 px-4 py-2 text-sm hover:border-accent-cta">Retake</Link>
            ) : (
              <Link href="/interview" className={cta}>Start</Link>
            )}
          </div>
        </>
      )}

      {/* Step 4 — results */}
      <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-primary/50">{hasInterview ? "4" : "3"} · Your results</h2>
      <div className={`${stepCard} mt-2`}>
        <div className="min-w-0 flex-1">
          <h3 className="text-base">Results, report &amp; roadmap</h3>
          <p className="mt-0.5 text-xs text-primary/60">
            {anySubmitted ? "Explore your scores, your Summary of Findings and your development roadmap." : "Complete at least one exam to unlock your results."}
          </p>
        </div>
        {anySubmitted ? (
          <Link href="/results" className={cta}>View results</Link>
        ) : (
          <span className="text-xs text-primary/45">Locked</span>
        )}
      </div>
    </div>
  );
}
