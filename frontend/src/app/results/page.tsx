import type { Metadata } from "next";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import ResultsView from "./ResultsView";

export const metadata: Metadata = { title: "Your results · METI-MC" };

export default function ResultsPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-3xl px-6 py-10">
        <RequireAuth roles={["candidate"]}>
          <ResultsView />
        </RequireAuth>
      </div>
    </main>
  );
}
