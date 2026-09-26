"use client";

import { useEffect, useRef, useState } from "react";

import { errorMessage } from "@/lib/api";
import { reportApi } from "@/lib/reports";

type Msg = { role: "you" | "explainer"; text: string };

/* eslint-disable @typescript-eslint/no-explicit-any */
function getRecognition(): any {
  if (typeof window === "undefined") return null;
  const Ctor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  return Ctor ? new Ctor() : null;
}

/** The AI Results Explainer chat (Phase 8): grounded in the candidate's own results.
 *  mode="why" on the report, mode="coach" on the roadmap. Voice via the browser Web Speech API. */
export default function Explainer({ mode }: { mode: "why" | "coach" }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [speak, setSpeak] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setVoiceSupported(!!getRecognition() && typeof window !== "undefined" && "speechSynthesis" in window);
  }, []);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const placeholder = mode === "coach" ? "e.g. What should I work on first?" : "e.g. Why is this a strength?";

  const send = async (question: string) => {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "you", text: q }]);
    setBusy(true);
    try {
      const reply = await reportApi.ask(q, mode);
      setMessages((m) => [...m, { role: "explainer", text: reply.answer }]);
      if (speak && voiceSupported) {
        const u = new SpeechSynthesisUtterance(reply.answer);
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(u);
      }
    } catch (err) {
      setMessages((m) => [...m, { role: "explainer", text: errorMessage(err) }]);
    } finally {
      setBusy(false);
    }
  };

  const startListening = () => {
    const rec = getRecognition();
    if (!rec) return;
    rec.lang = "en-US";
    rec.interimResults = false;
    setListening(true);
    rec.onresult = (e: any) => {
      const said = e.results[0][0].transcript;
      setInput(said);
      send(said);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    rec.start();
  };

  return (
    <div className="flex flex-col rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)]">
      <div className="border-b border-primary/10 px-5 py-3">
        <h3 className="font-heading text-sm font-semibold">{mode === "coach" ? "Ask your coach" : "Ask about your results"}</h3>
        <p className="text-xs text-primary/55">
          Grounded only in your own results{mode === "coach" ? " and roadmap" : ""} — nothing invented.
        </p>
      </div>

      <div className="max-h-80 min-h-[8rem] space-y-3 overflow-y-auto px-5 py-4">
        {messages.length === 0 ? (
          <p className="text-sm text-primary/50">Ask a question below{voiceSupported ? " — type it or tap the mic." : "."}</p>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`reveal-in text-sm ${m.role === "you" ? "text-right" : ""}`}>
              <span
                className={`inline-block max-w-[85%] rounded-lg px-3 py-2 ${
                  m.role === "you" ? "bg-accent-cta/20" : "bg-primary/5"
                }`}
              >
                {m.text}
              </span>
            </div>
          ))
        )}
        {busy && <p className="text-sm text-primary/50">Thinking…</p>}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex items-center gap-2 border-t border-primary/10 px-3 py-3"
      >
        {voiceSupported && (
          <>
            <button
              type="button"
              onClick={startListening}
              disabled={busy || listening}
              aria-label="Ask by voice"
              className={`rounded-full px-3 py-2 text-sm ${listening ? "bg-accent-cta text-primary" : "border border-primary/15 hover:bg-primary/5"}`}
            >
              {listening ? "● Listening" : "🎤"}
            </button>
            <button
              type="button"
              onClick={() => setSpeak((s) => !s)}
              aria-pressed={speak}
              aria-label="Read answers aloud"
              title="Read answers aloud"
              className={`rounded-full px-3 py-2 text-sm ${speak ? "bg-accent-cta text-primary" : "border border-primary/15 hover:bg-primary/5"}`}
            >
              🔊
            </button>
          </>
        )}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          className="min-w-0 flex-1 rounded-md border border-primary/15 bg-surface-card px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-md bg-accent-cta px-4 py-2 text-sm font-medium text-primary hover:bg-accent-cta/85 disabled:opacity-50"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
