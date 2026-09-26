"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth, type Role } from "@/lib/auth";

/** Renders children only for signed-in users (optionally holding one of `roles`); otherwise redirects to /login. */
export default function RequireAuth({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { state, hasRole } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (state.status === "signed_out") router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [state.status, router, pathname]);

  if (state.status !== "signed_in") {
    return (
      <p role="status" className="p-8 text-center text-sm text-primary/60">
        {state.status === "loading" ? "Checking your session…" : "Redirecting to sign in…"}
      </p>
    );
  }

  if (roles && !hasRole(roles)) {
    return (
      <div role="alert" className="mx-auto mt-16 max-w-md rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6 text-center">
        <h1 className="text-lg font-semibold">You don’t have access to this page</h1>
        <p className="mt-2 text-sm text-primary/60">
          It needs the {roles.join(" or ")} role. You’re signed in as {state.user.email} ({state.user.role}).
        </p>
        <Link href={state.user.role === "admin" ? "/admin" : "/account"} className="mt-4 inline-block text-sm underline">
          {state.user.role === "admin" ? "Go to Admin" : "Go to your account"}
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
