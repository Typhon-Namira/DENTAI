import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Check, Clock3, Crown, LoaderCircle, LockKeyhole, Sparkles, X } from "lucide-react";

import { api, authenticatedRequest, errorMessage, hasSession } from "../api/client";
import type { CurrentUser } from "../api/types";
import "./subscription-flow.css";

function secondsUntil(value: string | null): number | null {
  if (!value) return null;
  return Math.max(0, Math.floor((new Date(value).getTime() - Date.now()) / 1000));
}

function clock(total: number): string {
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, "0")).join(":");
}

function isFree(user: CurrentUser | null): boolean {
  return (user?.subscription_plan || "").toUpperCase() === "FREE";
}

function findSettingsButton(): HTMLButtonElement | null {
  const buttons = Array.from(document.querySelectorAll(".care-sidebar nav button")) as HTMLButtonElement[];
  return buttons.at(-1) ?? null;
}

export function SubscriptionExperience() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [settingsHost, setSettingsHost] = useState<HTMLElement | null>(null);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [confirmUpgrade, setConfirmUpgrade] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [previousState, setPreviousState] = useState("");

  const refresh = useCallback(async () => {
    if (!hasSession()) {
      setUser(null);
      return null;
    }
    try {
      const next = await api.me();
      setUser(next);
      setRemaining(secondsUntil(next.subscription_expires_at));
      return next;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 15000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setRemaining((current) => {
        if (!user?.subscription_expires_at) return current;
        return secondsUntil(user.subscription_expires_at);
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [user?.subscription_expires_at]);

  useEffect(() => {
    const sync = () => {
      const card = document.querySelector(".account-settings .subscription-card") as HTMLElement | null;
      setSettingsVisible(Boolean(document.querySelector(".account-settings")));
      if (!card) {
        setSettingsHost(null);
        return;
      }
      let host = document.getElementById("teta2-subscription-upgrade-host");
      if (!host) {
        host = document.createElement("div");
        host.id = "teta2-subscription-upgrade-host";
        card.appendChild(host);
      }
      setSettingsHost(host);
    };
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  const effectiveState = useMemo(() => {
    if (!user) return "";
    if (isFree(user) && remaining === 0 && user.subscription_state === "ACTIVE") return "FREE_EXPIRED";
    return user.subscription_state;
  }, [remaining, user]);

  useEffect(() => {
    if (!user) return;
    const target = document.querySelector(".care-subscription strong") as HTMLElement | null;
    if (!target) return;
    if (isFree(user)) {
      target.textContent = remaining === null ? "Free · 24 hours" : remaining > 0 ? `Free · ${clock(remaining)}` : "Free ended";
    } else if (effectiveState === "ACTIVE") {
      const days = remaining === null ? user.subscription_days_remaining : Math.ceil(remaining / 86400);
      target.textContent = days === null ? "Premium" : `Premium · ${days} days left`;
    } else if (effectiveState === "PAYMENT_REVIEW") {
      target.textContent = "Premium · approval pending";
    }
  });

  useEffect(() => {
    if (!user) return;
    if (previousState === "PAYMENT_REVIEW" && effectiveState === "ACTIVE" && !isFree(user)) {
      // Reload only the application state after approval. Tenant data is never
      // recreated; this simply makes every dashboard component read the new plan.
      window.location.reload();
      return;
    }
    setPreviousState(effectiveState);
  }, [effectiveState, previousState, user]);

  async function upgrade() {
    setBusy(true);
    setError("");
    try {
      await authenticatedRequest("/api/v1/platform/subscription/upgrade", { method: "POST" });
      setConfirmUpgrade(false);
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  function goSettings() {
    findSettingsButton()?.click();
  }

  if (!user) return null;

  const expired = effectiveState === "FREE_EXPIRED" || effectiveState === "EXPIRED";
  const pending = effectiveState === "PAYMENT_REVIEW";
  const showExpiredBlocker = expired && !settingsVisible;

  return <>
    {settingsHost && createPortal(
      <div className="subscription-upgrade-panel">
        {isFree(user) ? <>
          <div className="subscription-upgrade-copy"><span><Crown /></span><div><small>TETA2 PREMIUM</small><strong>Unlock the full clinic workspace for 30 days</strong><p>Unlimited patients, OPGs and tooth follow-up with your existing clinic history preserved.</p></div></div>
          <button className="care-primary" disabled={pending} onClick={() => setConfirmUpgrade(true)}>{pending ? <LoaderCircle className="subscription-spin" /> : <Sparkles />}{pending ? "Waiting for approval" : "Upgrade to Premium"}</button>
        </> : <div className="subscription-premium-active"><Check/><div><strong>Premium is active</strong><span>Your existing clinic workspace and history stay continuous.</span></div></div>}
      </div>,
      settingsHost
    )}

    {showExpiredBlocker && <div className="subscription-lock-layer" role="dialog" aria-modal="true">
      <div className="subscription-lock-card"><span className="subscription-lock-icon"><LockKeyhole /></span><small>FREE ACCESS ENDED</small><h2>Your 24-hour Free plan has finished.</h2><p>Your patients, OPGs, follow-up history, conversations and settings are still safely stored. Activate Premium to continue using Teta2 for the next 30 days.</p><div className="subscription-limit-summary"><span>✓ Same dashboard</span><span>✓ Same clinic data</span><span>✓ Unlimited Premium usage</span></div><button className="care-primary" onClick={goSettings}><Crown/>Go to Settings & activate Premium</button></div>
    </div>}

    {pending && <div className="subscription-lock-layer pending" role="dialog" aria-modal="true">
      <div className="subscription-lock-card pending"><div className="subscription-logo-loader"><span>Teta2</span><LoaderCircle /></div><small>PAYMENT REVIEW</small><h2>Premium activation is being confirmed.</h2><p>Your request has been sent to the Teta2 administration panel. Approval normally takes between <strong>1 and 6 hours</strong>.</p><div className="subscription-wait-line"><Clock3/><span>You can leave this page open. The dashboard will unlock automatically after approval.</span></div></div>
    </div>}

    {confirmUpgrade && <div className="subscription-confirm-layer" role="dialog" aria-modal="true">
      <div className="subscription-confirm-card"><button className="subscription-close" onClick={() => setConfirmUpgrade(false)}><X/></button><span className="subscription-lock-icon premium"><Crown/></span><small>CONFIRM UPGRADE</small><h2>Activate Teta2 Premium</h2><p>We already have your clinic details. Confirm once and we’ll send the payment instructions to <strong>{user.email}</strong> and place your account into payment review.</p><ul><li>30 days of Premium access after admin approval</li><li>No patient or OPG limits from the Free plan</li><li>Your existing dashboard and all clinic history remain unchanged</li></ul>{error&&<div className="care-inline-error">{error}</div>}<div className="subscription-confirm-actions"><button className="care-secondary" onClick={() => setConfirmUpgrade(false)}>Cancel</button><button className="care-primary" disabled={busy} onClick={() => void upgrade()}>{busy?<LoaderCircle className="subscription-spin"/>:<Check/>}{busy?"Submitting…":"Confirm & continue"}</button></div></div>
    </div>}
  </>;
}

function setTextIfChanged(node: Element | null, value: string) {
  if (node && node.textContent !== value) node.textContent = value;
}

export function FreemiumPublicExperience() {
  useEffect(() => {
    const update = () => {
      if (!["/register", "/request-access"].includes(window.location.pathname)) return;
      const story = document.querySelector(".pav2-access-story");
      setTextIfChanged(story?.querySelector("h1") ?? null, "Start Teta2 free for 24 hours.");
      setTextIfChanged(
        story?.querySelector(":scope > p") ?? null,
        "Submit your clinic details once and receive login credentials by email immediately. The one-time Free plan includes 3 patients, 1 OPG per patient and 1 tooth follow-up per OPG."
      );
      document.querySelectorAll(".pav2-market-preview, .pav2-live-price").forEach((node) => {
        const element = node as HTMLElement;
        if (element.style.display !== "none") element.style.display = "none";
      });
      setTextIfChanged(
        document.querySelector(".pav2-form-footer p"),
        "No payment is required for the one-time 24-hour Free plan. Upgrade to Premium from the dashboard when you are ready to continue."
      );
      const success = document.querySelector(".pav2-success");
      setTextIfChanged(success?.querySelector("h2") ?? null, "Free access activated");
      setTextIfChanged(
        success?.querySelector("p") ?? null,
        "Your Teta2 Free dashboard is ready. Login credentials have been sent to your email."
      );
    };

    update();
    window.addEventListener("popstate", update);
    const observer = new MutationObserver(update);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => {
      window.removeEventListener("popstate", update);
      observer.disconnect();
    };
  }, []);
  return null;
}
