"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import QuestionField from "@/components/engine/QuestionField";
import { ApiError, errorMessage } from "@/lib/api";
import { answerProblem, engineApi, isSkipped, type Answer, type Answers, type Attempt } from "@/lib/engine";

type SaveState = "saved" | "saving" | "unsaved" | "error";
type Load = { kind: "loading" } | { kind: "ready"; attempt: Attempt } | { kind: "locked"; message: string } | { kind: "error"; message: string };

const AUTOSAVE_MS = 800;
const primary = "rounded-md bg-accent-cta px-5 py-2.5 text-sm font-medium text-primary transition-colors hover:bg-accent-cta/85 disabled:opacity-50";
const secondary = "rounded-md border border-primary/20 px-5 py-2.5 text-sm transition-colors hover:border-accent-cta disabled:opacity-40";

export default function Runner() {
  const { code } = useParams<{ code: string }>();
  const [load, setLoad] = useState<Load>({ kind: "loading" });

  useEffect(() => {
    let stop = false;
    engineApi
      .start(code)
      .then((attempt) => !stop && setLoad({ kind: "ready", attempt }))
      .catch((err) => {
        if (stop) return;
        if (err instanceof ApiError && (err.status === 402 || err.status === 404)) setLoad({ kind: "locked", message: errorMessage(err) });
        else setLoad({ kind: "error", message: errorMessage(err) });
      });
    return () => {
      stop = true;
    };
  }, [code]);

  if (load.kind === "loading") return <p role="status" className="text-sm text-primary/60">Loading your assessment…</p>;
  if (load.kind !== "ready") {
    return (
      <div role="alert" className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-8 text-center">
        <h1 className="text-xl">{load.kind === "locked" ? "This assessment isn’t available" : "Something went wrong"}</h1>
        <p className="mt-2 text-sm text-primary/60">{load.message}</p>
        <div className="mt-6 flex justify-center gap-3">
          {load.kind === "locked" && (
            <Link href="/pricing" className={primary}>
              See pricing
            </Link>
          )}
          <Link href="/assessments" className={secondary}>
            Your assessments
          </Link>
        </div>
      </div>
    );
  }
  return <AttemptView initial={load.attempt} />;
}

const AUTO_ADVANCE_TYPES = new Set(["single_choice", "likert"]);
const AUTO_ADVANCE_MS = 400;

function AttemptView({ initial }: { initial: Attempt }) {
  const defn = initial.definition;
  const [answers, setAnswers] = useState<Answers>(initial.answers);
  const [skipped, setSkipped] = useState<Set<string>>(new Set());
  const [status, setStatus] = useState(initial.status);
  const [save, setSave] = useState<SaveState>("saved");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [banner, setBanner] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Whole-exam timer from the admin-set time limit, anchored to when the attempt started so it keeps
  // counting across reloads/devices. 0 → no limit set.
  const limitSec = (defn.time_limit_minutes || 0) * 60;
  const deadline = useMemo(
    () => (limitSec ? new Date(initial.started_at).getTime() + limitSec * 1000 : 0),
    [limitSec, initial.started_at],
  );
  // Seeded with the full duration; the timer effect corrects it to the real remaining on mount.
  const [timeLeft, setTimeLeft] = useState<number | null>(limitSec || null);
  const timedOut = useRef(false);

  // One flat list of questions across the visible (non-skipped) sections — the exam runs
  // question by question, not section by section.
  const flat = useMemo(
    () =>
      defn.sections
        .filter((s) => !isSkipped(s, answers))
        .flatMap((s) => s.questions.map((q, i) => ({ q, section: s, firstInSection: i === 0 }))),
    [defn.sections, answers],
  );
  const total = flat.length;
  const [pos, setPos] = useState(0);
  const onReview = pos >= total;
  const current = onReview ? null : flat[Math.min(pos, total - 1)];

  // --- autosave -----------------------------------------------------------------------------
  const pending = useRef<Record<string, Answer | null>>({});
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const advanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inFlight = useRef<Promise<void> | null>(null);
  const retry = useRef<() => void>(() => {});

  const flush = useCallback(
    async (sectionKey?: string): Promise<boolean> => {
      if (timer.current) clearTimeout(timer.current);
      await inFlight.current;
      const batch = pending.current;
      if (!Object.keys(batch).length && !sectionKey) return true;
      pending.current = {};
      setSave("saving");
      let ok = true;
      inFlight.current = engineApi
        .save(initial.id, batch, sectionKey)
        .then(() => setSave(Object.keys(pending.current).length ? "unsaved" : "saved"))
        .catch(() => {
          ok = false;
          pending.current = { ...batch, ...pending.current };
          setSave("error");
          timer.current = setTimeout(() => retry.current(), 3000);
        });
      await inFlight.current;
      inFlight.current = null;
      return ok;
    },
    [initial.id],
  );

  useEffect(() => {
    retry.current = () => void flush();
  }, [flush]);

  const goTo = useCallback(
    (next: number) => {
      if (advanceTimer.current) clearTimeout(advanceTimer.current);
      setBanner("");
      setPos(Math.max(0, Math.min(next, total)));
      window.scrollTo({ top: 0, behavior: "smooth" });
      void flush();
    },
    [flush, total],
  );

  const setAnswer = (key: string, value: Answer | null, opts?: { autoAdvance?: boolean }) => {
    setAnswers((prev) => {
      const next = { ...prev };
      if (value === null) delete next[key];
      else next[key] = value;
      return next;
    });
    setSkipped((prev) => {
      if (!prev.has(key)) return prev;
      const n = new Set(prev);
      n.delete(key); // answering un-skips it
      return n;
    });
    setErrors((prev) => ({ ...prev, [key]: "" }));
    pending.current[key] = value;
    setSave("unsaved");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => flush(), AUTOSAVE_MS);
    if (opts?.autoAdvance) {
      if (advanceTimer.current) clearTimeout(advanceTimer.current);
      advanceTimer.current = setTimeout(() => setPos((p) => Math.min(p + 1, total)), AUTO_ADVANCE_MS);
    }
  };

  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (Object.keys(pending.current).length) e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);
  useEffect(() => () => {
    if (advanceTimer.current) clearTimeout(advanceTimer.current);
  }, []);

  const skip = (key: string) => {
    if (answers[key] === undefined) setSkipped((prev) => new Set(prev).add(key));
    goTo(pos + 1);
  };

  const next = () => {
    if (!current) return;
    const problem = answerProblem(current.q, answers[current.q.key]);
    if (problem) {
      setErrors((prev) => ({ ...prev, [current.q.key]: problem }));
      setBanner("Answer this question, or use Skip if you're not sure.");
      return;
    }
    goTo(pos + 1);
  };

  const submit = async () => {
    setSubmitting(true);
    setBanner("");
    if (!(await flush())) {
      setBanner("Your latest answers haven’t saved yet — check your connection and try again.");
      setSubmitting(false);
      return;
    }
    try {
      await engineApi.submit(initial.id, [...skipped]);
      setStatus("submitted");
    } catch (err) {
      const fieldErrors = ((err as ApiError).body as { errors?: { field: string; message: string; section_key?: string }[] })?.errors ?? [];
      setErrors(Object.fromEntries(fieldErrors.map((e) => [e.field, e.message])));
      const firstKey = fieldErrors[0]?.field;
      const target = firstKey ? flat.findIndex((f) => f.q.key === firstKey) : -1;
      setBanner(errorMessage(err));
      if (target >= 0) setPos(target);
    } finally {
      setSubmitting(false);
    }
  };

  // When the exam time runs out, submit whatever's done — everything unanswered counts as skipped.
  const autoSubmitOnTimeout = useCallback(async () => {
    if (timedOut.current || status !== "in_progress") return;
    timedOut.current = true;
    setBanner("Time's up — your exam has been submitted.");
    await flush();
    const unanswered = flat.filter((f) => answerProblem(f.q, answers[f.q.key])).map((f) => f.q.key);
    try {
      await engineApi.submit(initial.id, [...new Set([...skipped, ...unanswered])]);
      setStatus("submitted");
    } catch {
      /* leave the banner; the candidate can press submit */
    }
  }, [status, flush, flat, answers, skipped, initial.id]);

  // Tick the exam timer once a second.
  useEffect(() => {
    if (!deadline || status !== "in_progress") return;
    const tick = () => {
      const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
      setTimeLeft(left);
      if (left <= 0) void autoSubmitOnTimeout();
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [deadline, status, autoSubmitOnTimeout]);

  const answeredCount = flat.filter((f) => !answerProblem(f.q, answers[f.q.key])).length;
  const pct = total ? Math.round((Math.min(pos, total) / total) * 100) : 0;
  const mmss = timeLeft == null ? null : `${Math.floor(timeLeft / 60)}:${String(timeLeft % 60).padStart(2, "0")}`;

  if (status === "submitted") {
    return (
      <div role="status" className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-10 text-center reveal">
        <p aria-hidden className="text-4xl text-accent-cta">✓</p>
        <h1 className="mt-2 text-2xl">{defn.name} submitted</h1>
        <p className="mt-2 text-primary/70">Thank you. Your answers are locked and your results are ready.</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/results" className={primary}>See your results</Link>
          <Link href="/assessments" className={secondary}>Back to your assessments</Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="sticky top-0 z-10 -mx-6 mb-6 border-b border-primary/10 bg-surface-base/95 px-6 py-3 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="font-heading font-semibold">{defn.name}</span>
          <span className="flex items-center gap-3">
            {mmss && (
              <span
                className={`rounded-full px-2.5 py-1 text-xs font-medium tabular-nums ${timeLeft != null && timeLeft <= 60 ? "bg-red-100 text-red-700" : "bg-primary/5 text-primary/70"}`}
                aria-live="polite"
                title="Time remaining for this exam"
              >
                ⏱ {mmss}
              </span>
            )}
            <span className="text-xs text-primary/60" aria-live="polite">
              {save === "saved" && "✓ All changes saved"}
              {save === "saving" && "Saving…"}
              {save === "unsaved" && "Unsaved changes"}
              {save === "error" && <span className="text-red-700">Not saved — retrying…</span>}
            </span>
          </span>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-primary/10" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Progress">
          <div className="h-full rounded-full bg-accent-cta animate-bar" style={{ width: `${pct}%` }} />
        </div>
        <p className="mt-1 text-xs text-primary/55">
          {onReview ? "Review" : `Question ${pos + 1} of ${total}`} · {answeredCount} answered
          {skipped.size ? ` · ${skipped.size} skipped` : ""}
          {defn.time_limit_minutes ? ` · ${defn.time_limit_minutes} min exam` : ""}
        </p>
      </div>

      {banner && <p role="alert" className="mb-6 rounded-md bg-red-50 px-4 py-3 text-sm text-red-800">{banner}</p>}

      {current ? (
        <section aria-labelledby="q-title" key={current.q.key} className="reveal">
          {current.firstInSection && (
            <div className="mb-4">
              <h1 id="q-title" className="text-xl">{current.section.title}</h1>
              {current.section.instructions && <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-primary/70">{current.section.instructions}</p>}
            </div>
          )}
          <QuestionField
            question={current.q}
            number={pos + 1}
            value={answers[current.q.key]}
            onChange={(v) => setAnswer(current.q.key, v, { autoAdvance: AUTO_ADVANCE_TYPES.has(current.q.type) })}
            onUpload={async (file) => {
              const res = await engineApi.upload(initial.id, current.q.key, file);
              delete pending.current[current.q.key];
              setAnswers((prev) => ({ ...prev, [current.q.key]: res.answer }));
              setSkipped((prev) => {
                const n = new Set(prev);
                n.delete(current.q.key);
                return n;
              });
              setErrors((prev) => ({ ...prev, [current.q.key]: "" }));
            }}
            error={errors[current.q.key]}
          />
          <div className="mt-8 flex items-center justify-between gap-3">
            <button className={secondary} onClick={() => goTo(pos - 1)} disabled={pos === 0}>Back</button>
            <div className="flex gap-3">
              <button className={secondary} onClick={() => skip(current.q.key)}>Skip</button>
              <button className={primary} onClick={next}>{pos === total - 1 ? "Review" : "Next"}</button>
            </div>
          </div>
          <p className="mt-3 text-center text-xs text-primary/45">Not sure? Use <span className="font-medium">Skip</span> — you can come back to it from Review.</p>
        </section>
      ) : (
        <section aria-labelledby="review-title" className="reveal">
          <h1 id="review-title" className="text-2xl">Review and submit</h1>
          <p className="mt-2 text-primary/70">
            {answeredCount} of {total} answered{skipped.size ? `, ${skipped.size} skipped` : ""}. Skipped questions are marked wrong — you can still answer them. Once you submit, your answers are locked.
          </p>
          <ul className="mt-6 divide-y divide-primary/10 rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)]">
            {flat.map((f, i) => {
              const done = !answerProblem(f.q, answers[f.q.key]);
              const isSkip = skipped.has(f.q.key) && !done;
              return (
                <li key={f.q.key} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
                  <span className="min-w-0 flex-1 truncate">
                    <span className={`mr-2 ${done ? "text-accent-cta" : isSkip ? "text-primary/40" : "text-red-700"}`}>{done ? "✓" : isSkip ? "–" : "!"}</span>
                    {i + 1}. {f.q.prompt}
                  </span>
                  <button className="shrink-0 text-xs underline decoration-accent-cta underline-offset-2" onClick={() => goTo(i)}>
                    {done ? "edit" : "answer"}
                  </button>
                </li>
              );
            })}
          </ul>
          <div className="mt-8 flex justify-between gap-3">
            <button className={secondary} onClick={() => goTo(total - 1)}>Back</button>
            <button className={primary} onClick={submit} disabled={submitting}>
              {submitting ? "Submitting…" : "Submit assessment"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
