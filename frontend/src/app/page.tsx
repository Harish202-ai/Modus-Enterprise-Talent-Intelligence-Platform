import Link from "next/link";

import SiteHeader from "@/components/SiteHeader";

import LandingView from "./LandingView";

// Landing & orientation (Phase 3): all copy comes from the published `site_content` "landing" document.
export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="flex-1">
        <LandingView />
      </div>
      <footer className="flex flex-wrap justify-center gap-6 border-t border-primary/10 px-6 py-6 text-xs text-primary/55">
        <span>© METI-MC · Modus Enterprise Transformation</span>
        <Link href="/status" className="hover:underline">
          System status
        </Link>
      </footer>
    </main>
  );
}
