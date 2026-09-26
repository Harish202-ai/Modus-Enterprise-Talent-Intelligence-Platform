import type { Metadata } from "next";

import SiteHeader from "@/components/SiteHeader";

import SystemStatus from "../SystemStatus";

export const metadata: Metadata = { title: "System status · METI-MC" };

export default function StatusPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="flex flex-1 items-start justify-center px-6 py-16">
        <SystemStatus />
      </div>
    </main>
  );
}
