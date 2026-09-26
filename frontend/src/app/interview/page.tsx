import type { Metadata } from "next";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import InterviewView from "./InterviewView";

export const metadata: Metadata = { title: "Video interview · METI-MC" };

export default function InterviewPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-2xl px-6 py-10">
        <RequireAuth roles={["candidate"]}>
          <InterviewView />
        </RequireAuth>
      </div>
    </main>
  );
}
