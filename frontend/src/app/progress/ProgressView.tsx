"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { errorMessage } from "@/lib/api";
import { progressApi, type Comparison, type ProgressOverviewRow } from "@/lib/progress";

const card = "rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6";
const NAMES: Record<string, string> = {
  talent_dna: "Talent DNA",
  values: "Values",
  capability: "Consulting Capability",
  written_communication: "Written Communication",
  case_study: "Case Study",
};

function Delta({ value }: { value: number | null }) {
  if (value === null) return <span className="text-primary/40">—</span>;
  if (value > 0) return <span className="text-accent-cta">▲ +{value}</span>;
  if (value < 0) return <span className="text-primary/50">▼ {value}</span>;
  return <span className="text-primary/50">no change</span>;
}

function CompareCard({ row }: { row: ProgressOverviewRow }) {
  const [cmp, setCmp] = useState<Comparison | null>(null);
  useEffect(() => {
    let stop = false;
    progressApi.compare(row.assessment_key).then((c) => !stop && setCmp(c));
    return () => {
      stop = true;
    };
  }, [row.assessment_key]);

  return (
    <section className={`${card} reveal`}>
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-lg">{NAMES[row.assessment_key] ?? row.assessment_key}</h2>
        <span className="text-xs text-primary/55">{row.attempts} attempt{row.attempts === 1 ? "" : "s"}</span>
      </div>
      {!cmp ? (
        <p className="mt-2 text-sm text-primary/50">Loading…</p>
      ) : row.can_compare && cmp.rows ? (
        <table className="mt-4 w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-primary/55">
              <th className="pb-2">Area</th>
              <th className="pb-2 text-right">Before</th>
              <th className="pb-2 text-right">After</th>
              <th className="pb-2 text-right">Change</th>
            </tr>
          </thead>
          <tbody>
            {cmp.rows.map((r) => (
              <tr key={r.key} className="border-t border-primary/5">
                <td className="py-1.5">{r.name}</td>
                <td className="py-1.5 text-right tabular-nums text-primary/60">{r.before ?? "—"}</td>
                <td className="py-1.5 text-right tabular-nums">{r.after ?? "—"}</td>
                <td className="py-1.5 text-right tabular-nums"><Delta value={r.delta} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="mt-2 text-sm text-primary/60">
          One attempt so far.{" "}
          <Link href={`/assessments/${row.assessment_key}`} className="text-accent-cta hover:underline">
            Retake it
          </Link>{" "}
          to see your before/after.
        </p>
      )}
    </section>
  );
}

export default function ProgressView() {
  const [rows, setRows] = useState<ProgressOverviewRow[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stop = false;
    progressApi
      .overview()
      .then((r) => !stop && setRows(r))
      .catch((err) => !stop && setError(errorMessage(err)));
    return () => {
      stop = true;
    };
  }, []);

  if (error) return <p role="alert" className="text-sm text-red-700">{error}</p>;
  if (!rows) return <p role="status" className="text-sm text-primary/60">Loading your progress…</p>;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl">Your progress</h1>
        <p className="mt-1 text-sm text-primary/60">Retake an assessment any time — your earlier attempt is kept, and you&apos;ll see the change here.</p>
      </header>
      {rows.length === 0 ? (
        <div className={`${card} text-center`}>
          <p className="text-primary/70">Submit an assessment first, then come back to track your progress.</p>
          <Link href="/assessments" className="mt-4 inline-block text-sm font-medium text-accent-cta hover:underline">
            Go to your assessments →
          </Link>
        </div>
      ) : (
        rows.map((r) => <CompareCard key={r.assessment_key} row={r} />)
      )}
    </div>
  );
}
