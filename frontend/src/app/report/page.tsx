import type { Metadata } from "next";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import ReportView from "./ReportView";

export const metadata: Metadata = { title: "Your report · METI-MC" };

export default function ReportPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-3xl px-6 py-10">
        <RequireAuth roles={["candidate"]}>
          <ReportView />
        </RequireAuth>
      </div>
    </main>
  );
}
