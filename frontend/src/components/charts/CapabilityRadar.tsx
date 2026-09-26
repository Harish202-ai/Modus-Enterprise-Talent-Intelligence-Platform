import type { Competency } from "@/lib/scores";

/** Consulting Capability radar: a weighted % per competency the knowledge items cover. */
const SIZE = 340;
const C = SIZE / 2;
const R = 120;
const RINGS = [0.25, 0.5, 0.75, 1];

export default function CapabilityRadar({ competencies }: { competencies: Competency[] }) {
  const axes = competencies.length;
  if (axes < 3) {
    // A radar needs at least 3 axes; fall back to bars for a thin item bank.
    return (
      <ul className="space-y-3">
        {competencies.map((c) => (
          <li key={c.key} className="flex items-center justify-between gap-3 text-sm">
            <span className="font-medium">{c.name}</span>
            <span className="tabular-nums text-primary/60">{Math.round(c.weighted_pct)}%</span>
          </li>
        ))}
      </ul>
    );
  }
  const step = (2 * Math.PI) / axes;
  const at = (i: number, radius: number) => {
    const a = -Math.PI / 2 + i * step;
    return [C + Math.cos(a) * radius, C + Math.sin(a) * radius] as const;
  };
  const polygon = competencies.map((c, i) => at(i, (Math.max(0, Math.min(100, c.weighted_pct)) / 100) * R).join(",")).join(" ");

  return (
    <figure className="mx-auto w-full max-w-[360px]">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="Consulting capability radar" className="w-full">
        {RINGS.map((f) => (
          <polygon
            key={f}
            points={competencies.map((_, i) => at(i, R * f).join(",")).join(" ")}
            fill="none"
            stroke="var(--color-primary)"
            strokeOpacity="0.12"
          />
        ))}
        {competencies.map((_, i) => {
          const [x, y] = at(i, R);
          return <line key={i} x1={C} y1={C} x2={x} y2={y} stroke="var(--color-primary)" strokeOpacity="0.12" />;
        })}
        <polygon points={polygon} fill="var(--color-accent-cta)" fillOpacity="0.28" stroke="var(--color-accent-cta)" strokeWidth={2} />
        {competencies.map((c, i) => {
          const [x, y] = at(i, R + 16);
          const a = -Math.PI / 2 + i * step;
          const anchor = Math.abs(Math.cos(a)) < 0.34 ? "middle" : Math.cos(a) > 0 ? "start" : "end";
          return (
            <text key={c.key} x={x} y={y} textAnchor={anchor} dominantBaseline="middle" className="fill-primary text-[9px]">
              {c.name}
            </text>
          );
        })}
      </svg>
    </figure>
  );
}
