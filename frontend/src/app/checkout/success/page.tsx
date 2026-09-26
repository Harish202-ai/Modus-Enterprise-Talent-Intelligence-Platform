import type { Metadata } from "next";
import { Suspense } from "react";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

import SuccessView from "./SuccessView";

export const metadata: Metadata = { title: "Payment · METI-MC" };

export default function CheckoutSuccessPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-md px-6 py-20">
        <RequireAuth roles={["candidate"]}>
          <Suspense>
            <SuccessView />
          </Suspense>
        </RequireAuth>
      </div>
    </main>
  );
}
