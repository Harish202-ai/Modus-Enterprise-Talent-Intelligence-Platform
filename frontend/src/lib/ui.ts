/** Shared MODUS accent tokens for charts/rings/bars. */
export const accentHex = {
  violet: "#7b6ef6",
  blue: "#4f9cff",
  pink: "#ff7eb6",
  mint: "#2fd6ac",
  amber: "#ffb27a",
} as const;

export type Accent = keyof typeof accentHex;

export const accentSoft: Record<Accent, string> = {
  violet: "bg-violet/12 text-violet",
  blue: "bg-blue/12 text-blue",
  mint: "bg-mint-500/15 text-[#159c7a]",
  pink: "bg-pink/15 text-[#d64f8f]",
  amber: "bg-amber/20 text-[#c9762f]",
};

export const accentText: Record<Accent, string> = {
  violet: "text-violet",
  blue: "text-blue",
  mint: "text-[#159c7a]",
  pink: "text-[#d64f8f]",
  amber: "text-[#c9762f]",
};
