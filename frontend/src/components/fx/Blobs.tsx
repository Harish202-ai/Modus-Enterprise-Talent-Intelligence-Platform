import { cn } from "@/lib/cn";

/** Soft blurred pastel blobs for ambient depth. Purely decorative. */
export function Blobs({ className }: { className?: string }) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 -z-10 overflow-hidden", className)}>
      <div className="animate-blob absolute -left-24 -top-24 h-96 w-96 rounded-full bg-violet/30 blur-3xl" />
      <div className="animate-blob absolute right-[-6rem] top-10 h-[26rem] w-[26rem] rounded-full bg-blue/25 blur-3xl [animation-delay:-6s]" />
      <div className="animate-blob absolute bottom-[-8rem] left-1/3 h-80 w-80 rounded-full bg-pink/25 blur-3xl [animation-delay:-12s]" />
      <div className="animate-blob absolute bottom-10 right-1/4 h-72 w-72 rounded-full bg-mint-500/20 blur-3xl [animation-delay:-3s]" />
    </div>
  );
}
