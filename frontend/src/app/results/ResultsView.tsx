"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import CapabilityRadar from "@/components/charts/CapabilityRadar";
import EvidenceScores from "@/components/charts/EvidenceScores";
import TalentDnaBars from "@/components/charts/TalentDnaBars";
import ValuesWheel from "@/components/charts/ValuesWheel";
import { errorMessage } from "@/lib/api";
import { isScored, scoresApi, type AiScore, type Scores } from "@/lib/scores";

const card = "rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6";

function NotYet({ title, blurb }: { title: string; blurb: string }) {
  return (
    <section className={card}>
      <h2 className="text-lg">{title}</h2>
      <p className="mt-2 text-sm text-primary/60">{blurb}</p>
      <Link href="/assessments" className="mt-4 inline-block text-sm font-medium text-accent-cta hover:underline">
        Go to your assessments →
      </Link>
    </section>
  );
}

export default function ResultsView() {
  const [scores, setScores] = useState<Scores | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stop = false;
    scoresApi
      .mine()
      .then((s) => !stop && setScores(s))
      .catch((err) => !stop && setError(errorMessage(err)));
    return () => {
      stop = true;
    };
  }, []);

  if (error) return <p role="alert" className="text-sm text-red-700">{error}</p>;
  if (!scores) return <p role="status" className="text-sm text-primary/60">Loading your results…</p>;

  const { talent_dna, values, capability, written_communication, case_study } = scores;
  const anyScored =
    isScored(talent_dna) ||
    isScored(values) ||
    isScored(capability) ||
    written_communication.status !== "not_submitted" ||
    case_study.status !== "not_submitted";

  const patch = (partial: Partial<Scores>) => setScores((prev) => (prev ? { ...prev, ...partial } : prev));

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl">Your results</h1>
        <p className="mt-1 text-sm text-primary/60">
          These profiles are computed directly from your answers — the same answers always give the same result. Your written and case
          responses are reviewed separately, and your overall report follows.
        </p>
      </header>

      {!anyScored && (
        <NotYet
          title="No results yet"
          blurb="Complete the Talent DNA, Values or Consulting Capability assessment and your profile will appear here."
        />
      )}

      {/* Talent DNA */}
      {isScored(talent_dna) ? (
        <section className={card}>
          <h2 className="text-lg">Talent DNA</h2>
          <p className="mt-1 text-sm text-primary/60">How you naturally work, scored across nine dimensions.</p>
          <div className="mt-5">
            <TalentDnaBars dimensions={talent_dna.dimensions} />
          </div>
        </section>
      ) : (
        <NotYet title="Talent DNA" blurb="Rank the statements in the Talent DNA assessment to see your strongest working dimensions." />
      )}

      {/* Values */}
      {isScored(values) ? (
        <section className={card}>
          <h2 className="text-lg">Values</h2>
          <p className="mt-1 text-sm text-primary/60">
            Your value priorities, centred on your own average rating so they show what matters most to you relative to everything else.
          </p>
          <div className="mt-5">
            <ValuesWheel basic={values.basic} />
          </div>
          {values.higher_order.length > 0 && (
            <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {values.higher_order.map((h) => (
                <div key={h.key} className="rounded-md border border-primary/10 p-3 text-center">
                  <dt className="text-xs text-primary/60">{h.name}</dt>
                  <dd className={`mt-1 text-lg tabular-nums ${h.centered >= 0 ? "text-accent-cta" : "text-primary/50"}`}>
                    {h.centered >= 0 ? "+" : ""}
                    {h.centered.toFixed(1)}
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      ) : (
        <NotYet title="Values" blurb="Complete the Values assessment to see your Schwartz-informed values wheel." />
      )}

      {/* Consulting Capability */}
      {isScored(capability) ? (
        <section className={card}>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg">Consulting Capability</h2>
            <span className="text-sm text-primary/60">
              Overall <span className="font-heading text-base font-semibold text-primary">{Math.round(capability.overall_pct)}%</span> ·{" "}
              {capability.correct}/{capability.total} correct
            </span>
          </div>
          <p className="mt-1 text-sm text-primary/60">Knowledge across the consulting competencies the questions cover.</p>
          <div className="mt-5">
            <CapabilityRadar competencies={capability.competencies} />
          </div>
        </section>
      ) : (
        <NotYet title="Consulting Capability" blurb="Answer the Consulting Capability questions to see your competency radar." />
      )}

      <AiSection
        title="Written Communication"
        blurb="Your executive memo, scored on reasoning, knowledge and communication — each with the evidence behind it."
        score={written_communication}
        onRescored={(s) => patch({ written_communication: s })}
        assessmentKey="written_communication"
      />
      <AiSection
        title="Case Study"
        blurb="Your Harbour Bank answers, scored on reasoning, knowledge and communication with cited evidence."
        score={case_study}
        onRescored={(s) => patch({ case_study: s })}
        assessmentKey="case_study"
      />
    </div>
  );
}

function AiSection({
  title,
  blurb,
  score,
  assessmentKey,
  onRescored,
}: {
  title: string;
  blurb: string;
  score: AiScore;
  assessmentKey: string;
  onRescored: (s: AiScore) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (score.status === "not_submitted") {
    return <NotYet title={title} blurb={`Complete and submit the ${title} assessment to see this scored.`} />;
  }

  const rescore = async () => {
    setBusy(true);
    setError("");
    try {
      onRescored(await scoresApi.rescore(assessmentKey));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const pending = score.status === "pending";
  return (
    <section className={card}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg">{title}</h2>
        {(pending || score.status === "needs_review") && (
          <button
            onClick={rescore}
            disabled={busy}
            className="rounded-md border border-primary/15 px-3 py-1 text-sm hover:bg-primary/5 disabled:opacity-50"
          >
            {busy ? "Scoring…" : "Score now"}
          </button>
        )}
      </div>
      <p className="mt-1 text-sm text-primary/60">{blurb}</p>
      {error && <p role="alert" className="mt-2 text-sm text-red-700">{error}</p>}
      {pending ? (
        <p className="mt-4 text-sm text-primary/60">
          Your answer is being scored — this can take a moment. Check back shortly, or press “Score now”.
        </p>
      ) : (
        <div className="mt-5">
          <EvidenceScores responses={score.responses ?? []} />
        </div>
      )}
    </section>
  );
}
