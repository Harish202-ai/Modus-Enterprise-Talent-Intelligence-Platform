"use client";

import dynamic from "next/dynamic";

const AIOrb = dynamic(() => import("./AIOrb"), { ssr: false });

/** Client wrapper so server components can drop in the WebGL orb. */
export default function AIOrbLazy({ className }: { className?: string }) {
  return <AIOrb className={className} />;
}
