"use client";

import { useEffect, useRef, useState } from "react";

import { errorMessage } from "@/lib/api";
import { supportApi } from "@/lib/support";

type Msg = { role: "you" | "bot"; text: string };

/** Phase 10 — the site-wide support chatbot: a small floating bubble on every page.
 *  Answers general platform questions from public help content only (no candidate data). */
export default function SupportBubble() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([{ role: "bot", text: "Hi! Ask me anything about the platform — pricing, timing, privacy, how it works." }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "you", text: q }]);
    setBusy(true);
    try {
      const reply = await supportApi.chat(q);
      setMessages((m) => [...m, { role: "bot", text: reply.answer }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "bot", text: errorMessage(err) }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {open && (
        <div className="reveal-in mb-3 flex w-[min(22rem,calc(100vw-2rem))] flex-col rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] shadow-lg">
          <div className="flex items-center justify-between border-b border-primary/10 px-4 py-3">
            <span className="font-heading text-sm font-semibold">Help & support</span>
            <button onClick={() => setOpen(false)} aria-label="Close support chat" className="text-primary/50 hover:text-primary">
              ✕
            </button>
          </div>
          <div className="max-h-72 min-h-[6rem] space-y-2 overflow-y-auto px-4 py-3">
            {messages.map((m, i) => (
              <div key={i} className={`text-sm ${m.role === "you" ? "text-right" : ""}`}>
                <span className={`inline-block max-w-[85%] rounded-lg px-3 py-2 ${m.role === "you" ? "bg-accent-cta/20" : "bg-primary/5"}`}>{m.text}</span>
              </div>
            ))}
            {busy && <p className="text-sm text-primary/50">Looking that up…</p>}
            <div ref={endRef} />
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
            className="flex items-center gap-2 border-t border-primary/10 px-3 py-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question…"
              className="min-w-0 flex-1 rounded-md border border-primary/15 bg-surface-card px-3 py-2 text-sm"
            />
            <button type="submit" disabled={busy || !input.trim()} className="rounded-md bg-accent-cta px-3 py-2 text-sm font-medium text-primary hover:bg-accent-cta/85 disabled:opacity-50">
              Send
            </button>
          </form>
        </div>
      )}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? "Close help" : "Open help"}
        className="ml-auto flex h-12 w-12 items-center justify-center rounded-full bg-accent-cta text-lg text-primary shadow-lg transition-transform hover:scale-105"
      >
        {open ? "✕" : "?"}
      </button>
    </div>
  );
}
