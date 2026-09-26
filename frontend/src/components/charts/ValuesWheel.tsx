import type { BasicValue } from "@/lib/scores";

/**
 * Values wheel (TDD §9.2): the 10 basic values around the Schwartz circumplex, each drawn as a
 * radial bar out from a baseline ring. Length = the candidate's MRAT-centred priority — a value
 * they rate above their own average reaches outward (gold), below it points inward (muted). This
 * is real computed data, not a static image.
 */
const SIZE = 320;
const C = SIZE / 2;
const BASELINE = 74; // the "own average" ring
const REACH = 56; // max bar length either way

export default function ValuesWheel({ basic }: { basic: BasicValue[] }) {
  const maxAbs = Math.max(1, ...basic.map((b) => Math.abs(b.centered)));
  const scale = REACH / maxAbs;
  const step = (2 * Math.PI) / basic.length;

  return (
    <figure className="mx-auto w-full max-w-[340px]">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="Values wheel — priorities relative to your own average" className="w-full">
        {/* baseline ring = the candidate's own average */}
        <circle cx={C} cy={C} r={BASELINE} fill="none" stroke="var(--color-primary)" strokeOpacity="0.18" strokeDasharray="3 4" />
        {basic.map((b, i) => {
          const angle = -Math.PI / 2 + i * step; // first value at 12 o'clock, clockwise
          const cos = Math.cos(angle);
          const sin = Math.sin(angle);
          const r = BASELINE + b.centered * scale;
          const x2 = C + cos * r;
          const y2 = C + sin * r;
          const positive = b.centered >= 0;
          const labelR = BASELINE + REACH + 18;
          const lx = C + cos * labelR;
          const ly = C + sin * labelR;
          const anchor = Math.abs(cos) < 0.34 ? "middle" : cos > 0 ? "start" : "end";
          return (
            <g key={b.key}>
              <line
                x1={C + cos * BASELINE}
                y1={C + sin * BASELINE}
                x2={x2}
                y2={y2}
                stroke={positive ? "var(--color-accent-cta)" : "var(--color-primary)"}
                strokeOpacity={positive ? 1 : 0.4}
                strokeWidth={9}
                strokeLinecap="round"
              />
              <circle cx={x2} cy={y2} r={3.5} fill={positive ? "var(--color-accent-cta)" : "var(--color-primary)"} fillOpacity={positive ? 1 : 0.4} />
              <text x={lx} y={ly} textAnchor={anchor} dominantBaseline="middle" className="fill-primary text-[9px]">
                {b.name}
              </text>
            </g>
          );
        })}
        <circle cx={C} cy={C} r={3} fill="var(--color-primary)" fillOpacity="0.4" />
      </svg>
      <figcaption className="mt-1 text-center text-xs text-primary/55">
        Bars reaching outward are values you prioritise above your own average; inward, below it.
      </figcaption>
    </figure>
  );
}
