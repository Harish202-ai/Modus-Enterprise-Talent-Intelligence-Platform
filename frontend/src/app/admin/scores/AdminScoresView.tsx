"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { adminScoresApi, type QueueResponse, type QueueRow } from "@/lib/adminScores";
import { errorMessage } from "@/lib/api";

const card = "rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6";
const DIMS = [
  { key: "reasoning_score", label: "Reasoning" },
  { key: "knowledge_score", label: "Knowledge" },
  { key: "communication_score", label: "Communication" },
  { key: "overall_confidence", label: "Confidence" },
] as const;

function OverrideForm({ attemptId, resp, onDone }: { attemptId: string; resp: QueueResponse; onDone: () => void }) {
  const s = resp.scores;
  const [values, setValues] = useState<Record<string, number>>({
    reasoning_score: s?.reasoning_score ?? 50,
    knowledge_score: s?.knowledge_score ?? 50,
    communication_score: s?.communication_score ?? 50,
    overall_confidence: s?.overall_confidence ?? 70,
  });
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    if (reason.trim().length < 3) {
      setError("Please give a reason for the override.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await adminScoresApi.override(attemptId, resp.question_key, { ...(values as Required<typeof values>), reason } as never);
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-3 rounded-md border border-primary/10 p-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {DIMS.map((d) => (
          <label key={d.key} className="text-xs text-primary/60">
            {d.label}
            <input
              type="number"
              min={0}
              max={100}
              value={values[d.key]}
              onChange={(e) => setValues((v) => ({ ...v, [d.key]: Number(e.target.value) }))}
              className="mt-1 w-full rounded-md border border-primary/15 bg-surface-card px-2 py-1 text-sm text-primary"
            />
          </label>
        ))}
      </div>
      <input
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Reason for the override (required)"
        className="mt-3 w-full rounded-md border border-primary/15 bg-surface-card px-3 py-2 text-sm"
      />
      {error && <p className="mt-1 text-xs text-red-700">{error}</p>}
      <button onClick={submit} disabled={busy} className="mt-3 rounded-md bg-accent-cta px-4 py-2 text-sm font-medium text-primary hover:bg-accent-cta/85 disabled:opacity-50">
        {busy ? "Saving…" : "Save override"}
      </button>
    </div>
  );
}

export default function AdminScoresView() {
  const [queue, setQueue] = useState<QueueRow[] | null>(null);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let stop = false;
    adminScoresApi
      .queue()
      .then((q) => !stop && setQueue(q))
      .catch((err) => !stop && setError(errorMessage(err)));
    return () => {
      stop = true;
    };
  }, [reload]);

  if (error) return <p role="alert" className="text-sm text-red-700">{error}</p>;
  if (!queue) return <p role="status" className="text-sm text-primary/60">Loading AI marks…</p>;

  const needsReview = queue.filter((r) => r.needs_review);
  const marked = queue.filter((r) => !r.needs_review);
  const bump = () => setReload((n) => n + 1);

  return (
    <div className="space-y-6">
      <header>
        <Link href="/admin" className="text-sm text-accent-cta hover:underline">← Back to admin</Link>
        <h1 className="mt-2 text-2xl">AI marks</h1>
        <p className="mt-1 text-sm text-primary/60">
          The marks the AI gave to written and case answers. {marked.length} marked, {needsReview.length} need a human look. You can change any mark (with a reason).
        </p>
      </header>

      {queue.length === 0 && <div className={`${card} text-center text-sm text-primary/60`}>No written or case answers have been submitted yet.</div>}

      {needsReview.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-red-700">Needs your review</h2>
          {needsReview.map((row) => <RowCard key={row.attempt_id} row={row} onChange={bump} />)}
        </div>
      )}

      {marked.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-primary/50">Marked by AI</h2>
          {marked.map((row) => <RowCard key={row.attempt_id} row={row} onChange={bump} />)}
        </div>
      )}
    </div>
  );
}

const DIM_KEYS = [
  { key: "reasoning_score", label: "Reasoning" },
  { key: "knowledge_score", label: "Knowledge" },
  { key: "communication_score", label: "Communication" },
] as const;

function RowCard({ row, onChange }: { row: QueueRow; onChange: () => void }) {
  return (
    <section className={card}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-base">{row.candidate_email ?? row.attempt_id}</h3>
        <span className="text-xs text-primary/55">{row.assessment_key} · {row.status}</span>
      </div>
      {row.responses.map((r) => (
        <ResponseRow key={r.question_key} attemptId={row.attempt_id} resp={r} onChange={onChange} />
      ))}
      <button
        onClick={async () => {
          await adminScoresApi.approve(row.attempt_id);
          onChange();
        }}
        className="mt-4 rounded-md border border-primary/15 px-4 py-2 text-sm hover:bg-primary/5"
      >
        Approve
      </button>
    </section>
  );
}

function ResponseRow({ attemptId, resp, onChange }: { attemptId: string; resp: QueueResponse; onChange: () => void }) {
  const [editing, setEditing] = useState(false);
  const s = resp.scores;
  return (
    <div className="mt-4 border-t border-primary/5 pt-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium">
          {resp.prompt ? (resp.prompt.length > 70 ? `${resp.prompt.slice(0, 70)}…` : resp.prompt) : resp.question_key}
        </p>
        <span className="text-xs text-primary/55">{resp.status}{resp.override ? " · changed by admin" : ""}</span>
      </div>
      {s ? (
        <div className="mt-2 flex flex-wrap gap-4 text-sm">
          {DIM_KEYS.map((d) => (
            <span key={d.key} className="tabular-nums">
              <span className="text-primary/55">{d.label}:</span> <span className="font-medium">{s[d.key as keyof typeof s] as number}</span>
            </span>
          ))}
          <span className="tabular-nums text-primary/55">confidence {s.overall_confidence}</span>
        </div>
      ) : (
        <p className="mt-1 text-sm text-primary/60">{resp.message ?? "No mark yet."}</p>
      )}
      {!editing ? (
        <button onClick={() => setEditing(true)} className="mt-2 text-xs text-accent-cta hover:underline">
          {s ? "Change this mark" : "Set a mark"}
        </button>
      ) : (
        <OverrideForm attemptId={attemptId} resp={resp} onDone={() => { setEditing(false); onChange(); }} />
      )}
    </div>
  );
}
