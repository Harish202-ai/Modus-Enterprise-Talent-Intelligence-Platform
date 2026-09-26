"use client";

import { motion } from "framer-motion";
import { accentHex, type Accent } from "@/lib/ui";
import { cn } from "@/lib/cn";

export function ProgressBar({ value, accent = "violet", className }: { value: number; accent?: Accent; className?: string }) {
  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-full bg-ink/8", className)}>
      <motion.div
        initial={{ width: 0 }}
        whileInView={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        viewport={{ once: true }}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        className="h-full rounded-full"
        style={{ background: `linear-gradient(90deg, ${accentHex[accent]}, ${accentHex[accent]}cc)` }}
      />
    </div>
  );
}

export function ScoreRing({ value, size = 168, stroke = 14, accent = "violet", label, sub }: { value: number; size?: number; stroke?: number; accent?: Accent; label?: string; sub?: string }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - Math.max(0, Math.min(100, value)) / 100);
  const id = `ring-${accent}-${size}`;
  return (
    <div className="relative inline-grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={accentHex[accent]} />
            <stop offset="100%" stopColor="#4f9cff" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(17,24,39,0.07)" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={`url(#${id})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          whileInView={{ strokeDashoffset: offset }}
          viewport={{ once: true }}
          transition={{ duration: 1.3, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      <div className="absolute grid place-items-center text-center">
        <span className="font-heading text-4xl font-extrabold text-ink">{label ?? value}</span>
        {sub && <span className="mt-0.5 text-xs font-medium text-muted">{sub}</span>}
      </div>
    </div>
  );
}
