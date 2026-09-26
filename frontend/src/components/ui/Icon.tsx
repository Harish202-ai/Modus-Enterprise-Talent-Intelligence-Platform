import { cn } from "@/lib/cn";

/** Minimal stroke icon set — no external icon dependency. */
const paths: Record<string, React.ReactNode> = {
  dashboard: <><rect x="3" y="3" width="7" height="9" rx="2" /><rect x="14" y="3" width="7" height="5" rx="2" /><rect x="14" y="12" width="7" height="9" rx="2" /><rect x="3" y="16" width="7" height="5" rx="2" /></>,
  profile: <><circle cx="12" cy="8" r="4" /><path d="M4 20c0-3.5 3.6-6 8-6s8 2.5 8 6" /></>,
  assessments: <><rect x="5" y="3" width="14" height="18" rx="2.5" /><path d="M9 8h6M9 12h6M9 16h4" /></>,
  results: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
  talent: <><path d="M12 3a5 5 0 0 1 5 5c0 2-1 3-1 5H8c0-2-1-3-1-5a5 5 0 0 1 5-5Z" /><path d="M9 18h6M10 21h4" /></>,
  career: <><path d="M4 20l6-6 4 4 6-8" /><path d="M17 10h4v4" /></>,
  roadmap: <><path d="M6 3v14a3 3 0 0 0 3 3h9" /><circle cx="6" cy="20" r="1.6" /><path d="M18 3h-4a2 2 0 0 0-2 2v3h6" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" /></>,
  candidates: <><circle cx="9" cy="8" r="3.2" /><path d="M3 20c0-3 2.7-5 6-5s6 2 6 5" /><path d="M16 4.5a3 3 0 0 1 0 7M21 20c0-2.4-1.4-4.2-3.6-4.8" /></>,
  questions: <><circle cx="12" cy="12" r="9" /><path d="M9.5 9a2.5 2.5 0 1 1 3.6 2.2c-.8.4-1.1 1-1.1 1.8" /><circle cx="12" cy="16.5" r="0.6" fill="currentColor" /></>,
  evaluations: <><path d="M12 3a9 9 0 1 0 9 9" /><path d="M12 7v5l3 2" /><path d="M16 3l2 2 3-3" /></>,
  reports: <><path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" /><path d="M14 3v5h5M9 14l2 2 3-4" /></>,
  brain: <><path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-1 5.5A3 3 0 0 0 8 18a2.5 2.5 0 0 0 4 .5" /><path d="M15 4a3 3 0 0 1 3 3 3 3 0 0 1 1 5.5A3 3 0 0 1 16 18a2.5 2.5 0 0 1-4 .5V4" /></>,
  chart: <><path d="M4 20h16" /><rect x="6" y="10" width="3" height="7" rx="1" /><rect x="11" y="6" width="3" height="11" rx="1" /><rect x="16" y="13" width="3" height="4" rx="1" /></>,
  spark: <><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" /><circle cx="12" cy="12" r="2.4" /></>,
  scale: <><path d="M12 3v18M7 21h10M6 7l-3 6a3 3 0 0 0 6 0L6 7ZM18 7l-3 6a3 3 0 0 0 6 0l-3-6ZM4 7h16" /></>,
  chat: <><path d="M4 5h16v11H9l-4 3v-3H4z" /><path d="M8 10h8M8 13h5" /></>,
  case: <><rect x="3" y="7" width="18" height="13" rx="2.5" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18" /></>,
  upload: <><path d="M12 16V5M8 9l4-4 4 4" /><path d="M5 19h14" /></>,
  logout: <><path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4" /><path d="M16 16l4-4-4-4M9 12h11" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.2-3.2" /></>,
  bell: <><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6Z" /><path d="M10 19a2 2 0 0 0 4 0" /></>,
  arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
  check: <><path d="M4 12l5 5L20 6" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  shield: <><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z" /><path d="M9 12l2 2 4-4" /></>,
  download: <><path d="M12 4v11M8 11l4 4 4-4" /><path d="M5 20h14" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  target: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /><circle cx="12" cy="12" r="0.6" fill="currentColor" /></>,
  doc: <><path d="M7 3h7l5 5v13H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" /><path d="M14 3v5h5" /></>,
  menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
  close: <><path d="M6 6l12 12M18 6 6 18" /></>,
  star: <><path d="m12 3 2.6 5.5 6 .8-4.4 4.2 1.1 6-5.3-2.9-5.3 2.9 1.1-6L3.4 9.3l6-.8L12 3Z" /></>,
  play: <><path d="M8 5v14l11-7z" /></>,
};

export function Icon({ name, className, size = 20, strokeWidth = 1.8 }: { name: keyof typeof paths | string; className?: string; size?: number; strokeWidth?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" className={cn("shrink-0", className)} aria-hidden>
      {paths[name] ?? paths.spark}
    </svg>
  );
}
