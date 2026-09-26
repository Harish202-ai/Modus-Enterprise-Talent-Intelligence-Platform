import type { Metadata } from "next";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import AccountView from "./AccountView";

export const metadata: Metadata = { title: "Your account · METI-MC" };

export default function AccountPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-2xl px-6 py-10">
        <RequireAuth>
          <AccountView />
        </RequireAuth>
      </div>
    </main>
  );
}
