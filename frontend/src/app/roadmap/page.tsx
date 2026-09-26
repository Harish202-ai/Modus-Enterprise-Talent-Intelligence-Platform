import type { Metadata } from "next";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import RoadmapView from "./RoadmapView";

export const metadata: Metadata = { title: "Your roadmap · METI-MC" };

export default function RoadmapPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-3xl px-6 py-10">
        <RequireAuth roles={["candidate"]}>
          <RoadmapView />
        </RequireAuth>
      </div>
    </main>
  );
}
