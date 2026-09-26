import type { TalentDimension } from "@/lib/scores";

/** Talent DNA (TDD §9.1): normalised 0–100 strength per dimension, strongest first. */
export default function TalentDnaBars({ dimensions }: { dimensions: TalentDimension[] }) {
  return (
    <ul className="space-y-3">
      {dimensions.map((d) => (
        <li key={d.key}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="font-medium">{d.label}</span>
            <span className="tabular-nums text-primary/60">{Math.round(d.normalized)}</span>
          </div>
          <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-primary/10">
            <div
              className="h-full rounded-full bg-accent-cta transition-[width] duration-500"
              style={{ width: `${d.normalized}%` }}
              role="meter"
              aria-valuenow={Math.round(d.normalized)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={d.label}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
