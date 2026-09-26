import type { Metadata } from "next";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import CandidatesView from "./CandidatesView";

export const metadata: Metadata = { title: "Candidates · METI-MC" };

export default function AdminUsersPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-4xl px-6 py-10">
        <RequireAuth roles={["admin"]}>
          <CandidatesView />
        </RequireAuth>
      </div>
    </main>
  );
}
