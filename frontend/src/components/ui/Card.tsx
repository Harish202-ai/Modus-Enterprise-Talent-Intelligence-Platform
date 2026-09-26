import { cn } from "@/lib/cn";

export function Card({ className, children, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("rounded-3xl border border-line bg-card p-6 shadow-[var(--shadow-soft)]", className)} {...rest}>
      {children}
    </div>
  );
}

export function GlassCard({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("glass-tint rounded-3xl p-6 shadow-[var(--shadow-soft)]", className)}>{children}</div>;
}

export function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 rounded-full bg-violet/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-violet-ink", className)}>
      {children}
    </span>
  );
}
