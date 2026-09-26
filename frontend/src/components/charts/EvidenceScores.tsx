import { DIMENSIONS, type AiResponse, type DimensionScores } from "@/lib/scores";

/** One AI-scored response: the three named dimensions, each with its score bar and cited evidence. */
function ResponseCard({ r }: { r: AiResponse }) {
  if (r.status !== "scored" || !r.scores) {
    const tone = r.status === "needs_review" ? "text-red-700" : "text-primary/60";
    return (
      <div className="rounded-md border border-primary/10 p-4">
        <p className="text-sm font-medium">{r.prompt ? truncate(r.prompt) : r.question_key}</p>
        <p className={`mt-1 text-sm ${tone}`}>{r.message ?? statusLabel(r.status)}</p>
      </div>
    );
  }
  const s = r.scores;
  return (
    <div className="rounded-md border border-primary/10 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-sm font-medium">{r.prompt ? truncate(r.prompt) : r.question_key}</p>
        <span className="shrink-0 text-xs text-primary/55">confidence {s.overall_confidence}</span>
      </div>
      <ul className="mt-3 space-y-3">
        {DIMENSIONS.map((d) => {
          const score = s[`${d.key}_score` as keyof DimensionScores] as number;
          const evidence = s[`${d.key}_evidence` as keyof DimensionScores] as string;
          return (
            <li key={d.key}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="font-medium">{d.label}</span>
                <span className="tabular-nums text-primary/60">{score}</span>
              </div>
              <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-primary/10">
                <div className="h-full rounded-full bg-accent-cta" style={{ width: `${score}%` }} role="meter" aria-valuenow={score} aria-valuemin={0} aria-valuemax={100} aria-label={d.label} />
              </div>
              {evidence && <p className="mt-1 text-xs italic text-primary/60">“{evidence}”</p>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function EvidenceScores({ responses }: { responses: AiResponse[] }) {
  return (
    <div className="space-y-4">
      {responses.map((r) => (
        <ResponseCard key={r.question_key} r={r} />
      ))}
    </div>
  );
}

function truncate(text: string, n = 90) {
  return text.length > n ? `${text.slice(0, n).trimEnd()}…` : text;
}

function statusLabel(status: AiResponse["status"]) {
  switch (status) {
    case "pending":
      return "Scoring in progress…";
    case "needs_transcript":
      return "Waiting to be transcribed and scored.";
    case "empty":
      return "No answer to score.";
    default:
      return "Awaiting review.";
  }
}
