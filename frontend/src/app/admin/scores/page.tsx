import type { Metadata } from "next";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import AdminScoresView from "./AdminScoresView";

export const metadata: Metadata = { title: "Score review · METI-MC" };

export default function AdminScoresPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-3xl px-6 py-10">
        <RequireAuth roles={["admin"]}>
          <AdminScoresView />
        </RequireAuth>
      </div>
    </main>
  );
}
