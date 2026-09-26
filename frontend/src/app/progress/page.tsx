import type { Metadata } from "next";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import ProgressView from "./ProgressView";

export const metadata: Metadata = { title: "Your progress · METI-MC" };

export default function ProgressPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-3xl px-6 py-10">
        <RequireAuth roles={["candidate"]}>
          <ProgressView />
        </RequireAuth>
      </div>
    </main>
  );
}
