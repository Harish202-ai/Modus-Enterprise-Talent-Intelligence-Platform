import type { Metadata } from "next";
import Link from "next/link";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import ContentAdmin from "./ContentAdmin";

export const metadata: Metadata = {
  title: "Content authoring · METI-MC Admin",
};

export default function AdminContentPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <RequireAuth roles={["admin"]}>
        <div className="px-6 pt-4">
          <Link href="/admin" className="text-sm text-accent-cta hover:underline">← Back to admin</Link>
        </div>
        <ContentAdmin />
      </RequireAuth>
    </main>
  );
}
