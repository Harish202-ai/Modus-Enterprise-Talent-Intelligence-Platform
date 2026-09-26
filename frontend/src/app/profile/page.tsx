import type { Metadata } from "next";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import ResumeReview from "./ResumeReview";

export const metadata: Metadata = { title: "Your CV profile · METI-MC" };

export default function ProfilePage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-3xl px-6 py-10">
        <RequireAuth roles={["candidate"]}>
          <ResumeReview />
        </RequireAuth>
      </div>
    </main>
  );
}
