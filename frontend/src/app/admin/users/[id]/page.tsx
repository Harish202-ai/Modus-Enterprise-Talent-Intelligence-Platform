import type { Metadata } from "next";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import CandidateDetailView from "./CandidateDetailView";

export const metadata: Metadata = { title: "Candidate · METI-MC" };

export default function AdminUserPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-3xl px-6 py-10">
        <RequireAuth roles={["admin"]}>
          <CandidateDetailView />
        </RequireAuth>
      </div>
    </main>
  );
}
