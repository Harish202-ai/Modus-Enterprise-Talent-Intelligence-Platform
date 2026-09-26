import type { Metadata } from "next";
import { Suspense } from "react";

import AuthForm from "@/components/AuthForm";
import SiteHeader from "@/components/SiteHeader";

export const metadata: Metadata = { title: "Sign in · METI-MC" };

export default function Page() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="flex flex-1 items-start justify-center px-6 py-16">
        <Suspense>
          <AuthForm mode="login" />
        </Suspense>
      </div>
    </main>
  );
}
