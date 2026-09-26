"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Explainer from "@/components/chat/Explainer";
import CountUp from "@/components/motion/CountUp";
import { errorMessage } from "@/lib/api";
import { reportApi, type SummaryReport } from "@/lib/reports";

const card = "rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6";

function Gauge({ label, value, suffix = "" }: { label: string; value: number | null; suffix?: string }) {
  return (
    <div className={`${card} text-center`}>
      <div className="font-heading text-4xl font-bold text-primary">
        {value === null ? "—" : <CountUp value={value} suffix={suffix} />}
      </div>
      <div className="mt-1 text-xs uppercase tracking-wide text-primary/55">{label}</div>
    </div>
  );
}

export default function ReportView() {
  const [report, setReport] = useState<SummaryReport | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stop = false;
    reportApi
      .summary()
      .then((r) => !stop && setReport(r))
      .catch((err) => !stop && setError(errorMessage(err)));
    return () => {
      stop = true;
    };
  }, []);

  if (error) return <p role="alert" className="text-sm text-red-700">{error}</p>;
  if (!report) return <p role="status" className="text-sm text-primary/60">Loading your report…</p>;

  if (!report.scored) {
    return (
      <div className={`${card} reveal text-center`}>
        <h1 className="text-2xl">Your report</h1>
        <p className="mt-2 text-primary/70">{report.headline}</p>
        <Link href="/assessments" className="mt-6 inline-block rounded-md bg-accent-cta px-4 py-2 text-sm font-medium text-primary hover:bg-accent-cta/85">
          Go to your assessments
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="reveal">
        <h1 className="text-2xl">Summary of Findings</h1>
        <p className="mt-1 text-primary/70">{report.headline}</p>
      </header>

      <div className="reveal reveal-1 grid grid-cols-2 gap-4">
        <Gauge label={`Readiness · ${report.readiness_band}`} value={report.readiness} />
        <Gauge label="Evidence confidence" value={report.evidence_confidence} suffix="/100" />
      </div>

      <section className={`${card} reveal reveal-2`}>
        <h2 className="text-lg">Your strengths</h2>
        <ul className="mt-3 space-y-3">
          {report.strengths.length === 0 && <li className="text-sm text-primary/60">Complete more assessments to surface strengths.</li>}
          {report.strengths.map((s) => (
            <li key={s.label} className="text-sm">
              <span className="font-medium">{s.label}.</span> <span className="text-primary/70">{s.detail}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className={`${card} reveal reveal-3`}>
        <h2 className="text-lg">Development themes</h2>
        <ul className="mt-3 space-y-3">
          {report.development_themes.length === 0 && <li className="text-sm text-primary/60">No clear gaps yet — keep going.</li>}
          {report.development_themes.map((s) => (
            <li key={s.label} className="text-sm">
              <span className="font-medium">{s.label}.</span> <span className="text-primary/70">{s.detail}</span>
            </li>
          ))}
        </ul>
      </section>

      <div className="reveal reveal-4 flex flex-wrap gap-3">
        <Link href="/results" className="rounded-md border border-primary/15 px-4 py-2 text-sm hover:bg-primary/5">
          See your full scores
        </Link>
        {report.has_detailed_report ? (
          <Link href="/roadmap" className="rounded-md bg-accent-cta px-4 py-2 text-sm font-medium text-primary hover:bg-accent-cta/85">
            Your development roadmap →
          </Link>
        ) : (
          <Link href="/pricing" className="rounded-md bg-accent-cta px-4 py-2 text-sm font-medium text-primary hover:bg-accent-cta/85">
            Unlock the Detailed Report & Roadmap
          </Link>
        )}
      </div>

      <Explainer mode="why" />
    </div>
  );
}
