import type { Metadata } from "next";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import Runner from "./Runner";

export const metadata: Metadata = { title: "Assessment · METI-MC" };

export default function AssessmentPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-3xl px-6 pb-16 pt-6">
        <RequireAuth roles={["candidate"]}>
          <Runner />
        </RequireAuth>
      </div>
    </main>
  );
}
