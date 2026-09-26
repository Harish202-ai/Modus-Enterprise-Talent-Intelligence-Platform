import type { Metadata } from "next";
import { Suspense } from "react";

import SiteHeader from "@/components/SiteHeader";

import PricingView from "./PricingView";

export const metadata: Metadata = { title: "Pricing · METI-MC" };

export default function PricingPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-4xl px-6 py-14">
        <div className="mb-10 text-center">
          <h1 className="text-3xl">Choose your assessment</h1>
          <p className="mt-2 text-primary/70">One-off prices. Every assessment includes your Summary of Findings.</p>
        </div>
        <Suspense>
          <PricingView />
        </Suspense>
      </div>
    </main>
  );
}
