import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Check, ChevronRight, LoaderCircle, ShieldCheck, Sparkles, WandSparkles } from "lucide-react";

import { careGenerationApi, type GenerationReadiness } from "../api/careGeneration";
import { api, errorMessage } from "../api/client";
import { productApi, type CarePlan } from "../api/product";
import type { AIAnalysis, PatientProfile } from "../api/types";

function title(value: string): string {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function selectedPatient(): string {
  return (document.querySelector(".care-quick-patient select") as HTMLSelectElement | null)?.value ?? "";
}

function ensureHost(): HTMLElement | null {
  const anchor = document.querySelector(".ai-results-shell");
  if (!anchor?.parentElement) return null;
  const existing = document.getElementById("care-generation-contract-panel");
  if (existing) return existing;
  const host = document.createElement("div");
  host.id = "care-generation-contract-panel";
  host.className = "care-enhancer-host analysis care-generation-contract-host";
  anchor.parentElement.insertBefore(host, anchor.nextSibling);
  return host;
}

function hideLegacyPanel(hidden: boolean): void {
  const legacy = document.getElementById("care-enhancer-analysis");
  if (legacy) legacy.style.display = hidden ? "none" : "";
}

export function CareGenerationContractPanel() {
  const [patientId, setPatientId] = useState("");
  const [host, setHost] = useState<HTMLElement | null>(null);

  useEffect(() => {
    const sync = () => {
      const active = Boolean(document.querySelector(".ai-page"));
      hideLegacyPanel(active);
      setPatientId(active ? selectedPatient() : "");
      setHost(active ? ensureHost() : null);
    };
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true, attributes: true });
    const timer = window.setInterval(sync, 750);
    return () => {
      observer.disconnect();
      window.clearInterval(timer);
      hideLegacyPanel(false);
    };
  }, []);

  if (!host || !patientId) return null;
  return createPortal(<GenerationPanel patientId={patientId} />, host);
}

function GenerationPanel({ patientId }: { patientId: string }) {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [plans, setPlans] = useState<CarePlan[]>([]);
  const [readiness, setReadiness] = useState<GenerationReadiness | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [done, setDone] = useState("");

  const latestAnalysis = useMemo<AIAnalysis | null>(() => {
    if (!profile?.ai_analyses.length) return null;
    return [...profile.ai_analyses].sort((left, right) => right.requested_at.localeCompare(left.requested_at))[0] ?? null;
  }, [profile]);

  const completedAnalysis = latestAnalysis?.status === "COMPLETED" ? latestAnalysis : null;

  const loadBase = useCallback(async (showLoader = true) => {
    if (showLoader) setLoading(true);
    try {
      const [nextProfile, nextPlans] = await Promise.all([
        api.patientProfile(patientId),
        productApi.carePlans(patientId)
      ]);
      setProfile(nextProfile);
      setPlans(nextPlans);
      setError("");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      if (showLoader) setLoading(false);
    }
  }, [patientId]);

  useEffect(() => { void loadBase(); }, [loadBase]);

  useEffect(() => {
    if (!latestAnalysis || latestAnalysis.status === "COMPLETED" || latestAnalysis.status === "FAILED") return;
    let stopped = false;
    const poll = async () => {
      if (stopped) return;
      await loadBase(false);
      if (!stopped) window.setTimeout(() => void poll(), 1800);
    };
    const timer = window.setTimeout(() => void poll(), 1200);
    return () => { stopped = true; window.clearTimeout(timer); };
  }, [latestAnalysis?.id, latestAnalysis?.status, loadBase]);

  useEffect(() => {
    if (!completedAnalysis) {
      setReadiness(null);
      return;
    }
    let active = true;
    careGenerationApi.readiness(completedAnalysis.id)
      .then((value) => {
        if (active) {
          setReadiness(value);
          setError("");
        }
      })
      .catch((reason: unknown) => {
        if (!active) return;
        const status = (reason as { status?: number }).status;
        if (status === 404) {
          setError("Care backend is not on the same release as this frontend. Generation is temporarily unavailable until the protected backend deployment completes.");
        } else {
          setError(errorMessage(reason));
        }
      });
    return () => { active = false; };
  }, [completedAnalysis?.id]);

  const plan = completedAnalysis ? plans.find((item) => item.analysis_id === completedAnalysis.id) : undefined;
  const generated = Boolean(plan && ["PENDING_APPROVAL", "ACTIVE", "PAUSED", "COMPLETED"].includes(plan.status));

  async function generate() {
    if (!completedAnalysis || !readiness?.ready) return;
    setBusy(true); setError(""); setDone("");
    try {
      const next = await careGenerationApi.generate(completedAnalysis.id);
      setPlans((items) => [next, ...items.filter((item) => item.id !== next.id)]);
      setDone(`Sequential follow-up plan generated for ${next.items.length} pathological tooth${next.items.length === 1 ? "" : "s"}.`);
      setReadiness(await careGenerationApi.readiness(completedAnalysis.id));
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  function openFollowUps() {
    const buttons = Array.from(document.querySelectorAll(".care-sidebar nav button")) as HTMLButtonElement[];
    buttons.find((button) => ["Follow-up plans", "Հետագա պլաններ"].includes(button.getAttribute("aria-label") ?? ""))?.click();
  }

  if (loading || !latestAnalysis) return null;

  if (!completedAnalysis) {
    return <section className="care-flow-banner care-card bottom-placement authoritative-generation-panel">
      <div className="flow-orb"><LoaderCircle className="spin" /></div>
      <div className="flow-copy"><span>AI FOLLOW-UP ORCHESTRATION</span><h2>Waiting for analysis to complete</h2><p>The Generate button will unlock automatically as soon as the current OPG analysis finishes. No page refresh is required.</p></div>
      <div className="flow-actions"><button className="care-primary" disabled><Sparkles />Generate with AI</button><small><ShieldCheck />Analysis status: {title(latestAnalysis.status)}</small></div>
    </section>;
  }

  const candidates = readiness?.candidates ?? [];
  return (
    <section className="care-flow-banner care-card bottom-placement authoritative-generation-panel">
      <div className="flow-orb"><WandSparkles /></div>
      <div className="flow-copy">
        <span>AI FOLLOW-UP ORCHESTRATION</span>
        <h2>{generated ? "Follow-up plan ready" : "Generate follow-up plan"}</h2>
        {readiness ? <>
          <p>{readiness.ready ? `${readiness.candidate_count} pathological/red tooth${readiness.candidate_count === 1 ? "" : "s"} can enter the plan. Confidence affects priority and review guidance, not eligibility.` : "No pathological tooth findings with a resolved FDI are available in this completed OPG analysis."}</p>
          <div className="flow-teeth">{candidates.slice(0, 16).map((candidate) => <span key={`${candidate.tooth_fdi}-${candidate.finding_id}`}>Tooth {candidate.tooth_fdi} · {title(candidate.finding_type)}{candidate.confidence == null ? "" : ` · ${Math.round(candidate.confidence * 100)}%`}{candidate.review_status === "CONFIRMED" ? " · reviewed" : ""}</span>)}</div>
          {readiness.review_recommended_count > 0 && <div className="review-advice"><ShieldCheck />Review recommended for {readiness.review_recommended_count} tooth{readiness.review_recommended_count === 1 ? "" : "s"}, but generation is available now.</div>}
        </> : <p>Checking pathological tooth eligibility with the care backend…</p>}
        {done && <div className="flow-success"><Check />{done}</div>}
        {error && <div className="care-inline-error">{error}</div>}
      </div>
      <div className="flow-actions">
        {generated ? <button className="care-primary" onClick={openFollowUps}>Open follow-up plans <ChevronRight /></button> : <button className="care-primary" disabled={!readiness?.ready || busy} onClick={() => void generate()}><Sparkles />{busy ? "Generating…" : "Generate with AI"}</button>}
        <small><ShieldCheck />Clinician review is recommended; doctor remains in control.</small>
      </div>
    </section>
  );
}
