"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { apiFetch, setAccessToken, setRefreshHandler } from "./api";

export type Role = "candidate" | "admin";

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  status: "active" | "disabled";
  consent_accepted_at: string | null;
  orientation: { video_key: string; video_version: number; watched_at: string } | null;
  last_login_at: string | null;
  created_at: string;
};

type SessionResponse = { access_token: string; token_type: "bearer"; expires_at: string; user: AuthUser };
export type Registration = {
  email: string;
  fullName: string;
  password: string;
  consent: boolean;
  orientation?: { video_key: string; video_version: number } | null;
};

type AuthState = { status: "loading" } | { status: "signed_out" } | { status: "signed_in"; user: AuthUser };

type AuthContextValue = {
  state: AuthState;
  user: AuthUser | null;
  register: (form: Registration) => Promise<AuthUser>;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  setUser: (user: AuthUser) => void;
  hasRole: (roles: Role[]) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" });
  const refreshing = useRef<Promise<string | null> | null>(null);

  const applySession = useCallback((session: SessionResponse) => {
    setAccessToken(session.access_token);
    setState({ status: "signed_in", user: session.user });
    return session.user;
  }, []);

  const signedOut = useCallback(() => {
    setAccessToken(null);
    setState({ status: "signed_out" });
  }, []);

  /** Renew the access token from the refresh cookie. Concurrent callers share one request. */
  const refresh = useCallback((): Promise<string | null> => {
    refreshing.current ??= apiFetch<SessionResponse>("/v1/auth/refresh", { method: "POST" })
      .then((session) => {
        applySession(session);
        return session.access_token;
      })
      .catch(() => {
        signedOut();
        return null;
      })
      .finally(() => {
        refreshing.current = null;
      });
    return refreshing.current;
  }, [applySession, signedOut]);

  useEffect(() => {
    setRefreshHandler(refresh);
    refresh(); // restore the session on page load
    return () => setRefreshHandler(null);
  }, [refresh]);

  const value = useMemo<AuthContextValue>(() => {
    const user = state.status === "signed_in" ? state.user : null;
    return {
      state,
      user,
      register: async ({ email, fullName, password, consent, orientation }) =>
        applySession(
          await apiFetch<SessionResponse>("/v1/auth/register", {
            method: "POST",
            body: JSON.stringify({ email, full_name: fullName, password, consent, orientation: orientation ?? null }),
          }),
        ),
      login: async (email, password) =>
        applySession(await apiFetch<SessionResponse>("/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) })),
      logout: async () => {
        try {
          await apiFetch<void>("/v1/auth/logout", { method: "POST" });
        } finally {
          signedOut();
        }
      },
      setUser: (next) => setState({ status: "signed_in", user: next }),
      hasRole: (roles) => !!user && roles.includes(user.role),
    };
  }, [state, applySession, signedOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

/** Where to send someone right after signing in. */
export function homeFor(user: AuthUser): string {
  return user.role === "admin" ? "/admin" : "/assessments";
}
