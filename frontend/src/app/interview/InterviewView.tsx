"use client";

/* eslint-disable @typescript-eslint/no-explicit-any, react-hooks/purity */
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, errorMessage } from "@/lib/api";
import { interviewApi, type InterviewConfig, type InterviewRecord } from "@/lib/interview";

type Phase = "loading" | "locked" | "intro" | "recording" | "uploading" | "done" | "error";
const primary = "rounded-md bg-accent-cta px-5 py-2.5 text-sm font-medium text-primary hover:bg-accent-cta/85 disabled:opacity-50";
// ~700ms per sample; 3 consecutive inattentive samples (~2s) → one warning.
const ATTENTION_WARN_SAMPLES = 3;
// MediaPipe FaceLandmarker loaded from CDN at runtime (face tracking + head pose). Model is Google's public asset.
const MP_BASE = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14";
const MP_MODEL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";

function pickMime(): string {
  const types = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm", "video/mp4"];
  const MR = (window as any).MediaRecorder;
  return (MR && types.find((t) => MR.isTypeSupported?.(t))) || "";
}

/** Head yaw/pitch (degrees) from MediaPipe's 4x4 column-major facial transformation matrix. */
function eulerFromMatrix(m: number[] | Float32Array): { yaw: number; pitch: number } {
  const r00 = m[0], r10 = m[1], r20 = m[2], r21 = m[6], r22 = m[10];
  const sy = Math.hypot(r00, r10);
  const pitch = (Math.atan2(r21, r22) * 180) / Math.PI;
  const yaw = (Math.atan2(-r20, sy) * 180) / Math.PI;
  return { yaw, pitch };
}

export default function InterviewView() {
  const [phase, setPhase] = useState<Phase>("loading");
  const [config, setConfig] = useState<InterviewConfig | null>(null);
  const [error, setError] = useState("");
  const [qIndex, setQIndex] = useState(0);
  const [remaining, setRemaining] = useState(0);
  const [warnings, setWarnings] = useState(0);
  const [awayNow, setAwayNow] = useState(false);
  const [awayReason, setAwayReason] = useState("");
  const [faceSupported, setFaceSupported] = useState(true);
  const [monitorLoading, setMonitorLoading] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [result, setResult] = useState<InterviewRecord | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<any>(null);
  const chunks = useRef<Blob[]>([]);
  const qTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const faceTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const landmarkerRef = useRef<any>(null);
  const startedAt = useRef<number>(0);
  const warningsRef = useRef(0);
  const answeredRef = useRef(0);
  const finishing = useRef(false);

  useEffect(() => {
    let stop = false;
    interviewApi
      .config()
      .then((c) => {
        if (stop) return;
        setConfig(c);
        setPhase("intro");
      })
      .catch((err) => {
        if (stop) return;
        if (err instanceof ApiError && err.status === 402) setPhase("locked");
        else {
          setError(errorMessage(err));
          setPhase("error");
        }
      });
    return () => {
      stop = true;
    };
  }, []);

  const cleanup = useCallback(() => {
    if (qTimer.current) clearInterval(qTimer.current);
    if (faceTimer.current) clearInterval(faceTimer.current);
    try { landmarkerRef.current?.close?.(); } catch {}
    landmarkerRef.current = null;
    try { window.speechSynthesis?.cancel(); } catch {}
    streamRef.current?.getTracks().forEach((t) => t.stop());
  }, []);
  useEffect(() => cleanup, [cleanup]);

  // The interviewer "asks" each question aloud (video-call feel).
  useEffect(() => {
    if (phase !== "recording" || !config) return;
    const prompt = config.questions[qIndex]?.prompt;
    if (!prompt || typeof window === "undefined" || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(prompt);
      u.rate = 1;
      u.onstart = () => setSpeaking(true);
      u.onend = () => setSpeaking(false);
      u.onerror = () => setSpeaking(false);
      window.speechSynthesis.speak(u);
    } catch {
      /* speech not available — the question is still shown as text */
    }
  }, [phase, qIndex, config]);

  const upload = useCallback(async (auto: boolean) => {
    const blob = new Blob(chunks.current, { type: chunks.current[0]?.type || "video/webm" });
    const meta = {
      warnings: warningsRef.current,
      auto_submitted: auto,
      answered: answeredRef.current,
      duration_seconds: Math.round((Date.now() - startedAt.current) / 1000),
    };
    setPhase("uploading");
    try {
      setResult(await interviewApi.submit(blob, meta));
      setPhase("done");
    } catch (err) {
      setError(errorMessage(err));
      setPhase("error");
    }
  }, []);

  const finish = useCallback(
    (auto: boolean) => {
      if (finishing.current) return;
      finishing.current = true;
      if (qTimer.current) clearInterval(qTimer.current);
      if (faceTimer.current) clearInterval(faceTimer.current);
      const rec = recorderRef.current;
      if (rec && rec.state !== "inactive") {
        rec.onstop = () => {
          streamRef.current?.getTracks().forEach((t) => t.stop());
          void upload(auto);
        };
        rec.stop();
      } else {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        void upload(auto);
      }
    },
    [upload],
  );

  const goToQuestion = useCallback(
    (idx: number) => {
      if (!config) return;
      if (idx >= config.questions.length) {
        finish(false);
        return;
      }
      answeredRef.current = idx; // reached this many questions
      setQIndex(idx);
      setRemaining(config.questions[idx].seconds);
    },
    [config, finish],
  );

  // Per-question countdown.
  useEffect(() => {
    if (phase !== "recording") return;
    if (qTimer.current) clearInterval(qTimer.current);
    qTimer.current = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          goToQuestion(qIndex + 1);
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => {
      if (qTimer.current) clearInterval(qTimer.current);
    };
  }, [phase, qIndex, goToQuestion]);

  const raiseWarning = useCallback(() => {
    warningsRef.current += 1;
    setWarnings(warningsRef.current);
    if (config && warningsRef.current >= config.max_warnings) finish(true);
  }, [config, finish]);

  const start = async () => {
    setError("");
    // Camera needs a secure context. localhost counts; a plain-http LAN/IP address does not.
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setError(
        window.isSecureContext === false
          ? "Your browser is blocking the camera because this page isn't on a secure connection. Open the site at http://localhost:3000 (not an IP address) or over https, then try again."
          : "This browser doesn't support camera capture. Please use a recent Chrome, Edge or Firefox on a laptop/desktop.",
      );
      return; // stay on the intro so the button remains for a retry
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: true });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      const mime = pickMime();
      const rec = new (window as any).MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      chunks.current = [];
      rec.ondataavailable = (e: any) => e.data?.size && chunks.current.push(e.data);
      rec.start(1000);
      recorderRef.current = rec;
      startedAt.current = Date.now();
      finishing.current = false;
      warningsRef.current = 0;
      setWarnings(0);
      setPhase("recording");
      goToQuestion(0);
      startFaceMonitor();
    } catch (err: any) {
      // Keep the candidate on the intro screen with a specific message + the button, so they can retry.
      const name = err?.name || "";
      const messages: Record<string, string> = {
        NotAllowedError: "Camera/microphone permission was blocked. Click the camera icon in your browser's address bar, allow access, then press ‘Allow camera & start’ again.",
        NotFoundError: "No camera or microphone was found. Connect one (or check it's enabled) and try again.",
        NotReadableError: "Your camera or microphone is being used by another app (Zoom, Teams, etc.). Close it and try again.",
        SecurityError: "The browser blocked the camera on this connection. Open the site at http://localhost:3000 or over https and try again.",
      };
      setError(messages[name] || "We couldn't access your camera and microphone. Please allow access when prompted and try again — the interview needs both.");
      streamRef.current?.getTracks().forEach((t) => t.stop());
    }
  };

  // Real attention monitoring with MediaPipe FaceLandmarker (loaded from CDN at runtime): detects
  // the face leaving the frame (turning back / stepping away) and the head turning or looking down.
  const startFaceMonitor = async () => {
    setMonitorLoading(true);
    let vision: any, landmarker: any;
    try {
      // Dynamic import the bundler won't try to resolve at build time.
      const dynamicImport = Function("u", "return import(u)") as (u: string) => Promise<any>;
      vision = await dynamicImport(MP_BASE);
      const fileset = await vision.FilesetResolver.forVisionTasks(`${MP_BASE}/wasm`);
      landmarker = await vision.FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MP_MODEL },
        runningMode: "VIDEO",
        numFaces: 1,
        outputFacialTransformationMatrixes: true,
      });
    } catch {
      setFaceSupported(false);
      setMonitorLoading(false);
      return; // recording still works; warnings just can't run
    }
    landmarkerRef.current = landmarker;
    setMonitorLoading(false);
    let badStreak = 0;
    faceTimer.current = setInterval(() => {
      const v = videoRef.current;
      const lm = landmarkerRef.current;
      if (!v || v.readyState < 2 || !lm) return;
      let res: any;
      try {
        res = lm.detectForVideo(v, performance.now());
      } catch {
        return;
      }
      let reason = "";
      if (!res?.faceLandmarks?.length) {
        reason = "no_face";
      } else {
        const m = res.facialTransformationMatrixes?.[0]?.data;
        if (m) {
          const { yaw, pitch } = eulerFromMatrix(m);
          if (Math.abs(yaw) > 25 || Math.abs(pitch) > 22) reason = "looking_away";
        }
      }
      if (reason) {
        badStreak += 1;
        setAwayNow(true);
        setAwayReason(reason);
        if (badStreak >= ATTENTION_WARN_SAMPLES) {
          badStreak = 0;
          raiseWarning();
        }
      } else {
        badStreak = 0;
        setAwayNow(false);
      }
    }, 700);
  };

  if (phase === "loading") return <p role="status" className="text-sm text-primary/60">Loading the interview…</p>;
  if (phase === "locked")
    return (
      <div className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-8 text-center">
        <h1 className="text-2xl">Video interview</h1>
        <p className="mt-2 text-primary/70">The video interview is part of the Management Consulting Assessment.</p>
        <Link href="/pricing" className={`${primary} mt-6 inline-block`}>See pricing</Link>
      </div>
    );

  const q = config?.questions[qIndex];

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-2xl">AI video interview</h1>
        <p className="mt-1 text-sm text-primary/60">
          {config?.questions.length} timed questions. Keep your face in view — after {config?.max_warnings} warnings the interview submits automatically.
        </p>
      </header>

      {error && <p role="alert" className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}

      <div className="relative overflow-hidden rounded-lg border border-primary/10 bg-black">
        <video ref={videoRef} muted playsInline className="aspect-video w-full object-cover" />
        {phase === "recording" && (
          <>
            <span className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 text-xs text-white">
              <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" /> REC
            </span>
            <span className="absolute right-3 top-3 rounded-full bg-black/60 px-2.5 py-1 text-xs text-white">
              Warnings {warnings}/{config?.max_warnings}
            </span>
            {speaking && (
              <span className="absolute bottom-3 left-3 flex items-center gap-1.5 rounded-full bg-accent-cta px-2.5 py-1 text-xs text-primary">
                🔊 Interviewer is asking…
              </span>
            )}
            {monitorLoading && (
              <span className="absolute left-1/2 top-3 -translate-x-1/2 rounded-full bg-black/60 px-2.5 py-1 text-xs text-white">
                Starting attention monitoring…
              </span>
            )}
            {awayNow && (
              <span className="absolute inset-x-0 bottom-0 bg-red-600/90 px-3 py-2 text-center text-sm font-medium text-white">
                {awayReason === "no_face" ? "Face not detected — stay in front of the camera" : "Please look at the camera"}
              </span>
            )}
          </>
        )}
      </div>

      {phase === "intro" && (
        <div className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-5">
          <p className="text-sm text-primary/75">
            The interviewer asks each question aloud with a countdown; the next question comes up automatically. Your webcam
            records throughout, and your <span className="font-medium">attention is monitored</span> — if you turn away, look down or
            leave the frame you&apos;ll get a warning, and after {config?.max_warnings} the interview submits automatically. Find a quiet,
            well-lit spot, use Chrome on a laptop/desktop, and allow camera + microphone when prompted.
          </p>
          <button className={`${primary} mt-4`} onClick={start}>Allow camera & start</button>
        </div>
      )}

      {phase === "recording" && q && (
        <div className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-5">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-xs uppercase tracking-wide text-primary/55">Question {qIndex + 1} of {config?.questions.length}</span>
            <span className={`tabular-nums text-sm font-medium ${remaining <= 10 ? "text-red-700" : "text-primary/70"}`}>{remaining}s</span>
          </div>
          <p className="mt-2 text-lg">{q.prompt}</p>
          <div className="mt-4 flex justify-between gap-3">
            <button className="rounded-md border border-primary/20 px-4 py-2 text-sm hover:border-accent-cta" onClick={() => goToQuestion(qIndex + 1)}>
              {qIndex === (config!.questions.length - 1) ? "Finish" : "Next question"}
            </button>
            <button className="rounded-md border border-primary/20 px-4 py-2 text-sm text-red-700 hover:bg-red-50" onClick={() => finish(false)}>
              End & submit
            </button>
          </div>
          {!faceSupported && (
            <p className="mt-3 text-xs text-primary/50">Attention monitoring couldn&apos;t load (offline or blocked CDN), so warnings are disabled — your recording is still saved.</p>
          )}
        </div>
      )}

      {phase === "uploading" && <p role="status" className="text-sm text-primary/60">Uploading your interview…</p>}

      {phase === "done" && result && (
        <div className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-8 text-center">
          <p aria-hidden className="text-4xl text-accent-cta">✓</p>
          <h2 className="mt-2 text-xl">Interview submitted</h2>
          <p className="mt-2 text-sm text-primary/70">
            {result.auto_submitted ? "It was submitted automatically after too many warnings. " : ""}
            {result.warnings} warning{result.warnings === 1 ? "" : "s"} recorded. Your recording is saved for review.
          </p>
          <Link href="/results" className={`${primary} mt-6 inline-block`}>Back to results</Link>
        </div>
      )}
    </div>
  );
}
