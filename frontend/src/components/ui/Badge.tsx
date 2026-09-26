import { cn } from "@/lib/cn";

type Accent = "violet" | "blue" | "pink" | "mint" | "amber" | "neutral";

const map: Record<Accent, string> = {
  violet: "bg-violet/12 text-violet-ink",
  blue: "bg-blue/12 text-[#2b6fd6]",
  pink: "bg-pink/15 text-[#d64f8f]",
  mint: "bg-mint-500/15 text-[#159c7a]",
  amber: "bg-amber/20 text-[#c9762f]",
  neutral: "bg-ink/6 text-muted",
};

export function Badge({ accent = "neutral", children, className }: { accent?: Accent; children: React.ReactNode; className?: string }) {
  return <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold", map[accent], className)}>{children}</span>;
}
