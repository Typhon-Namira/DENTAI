import { useEffect, useState } from "react";
import { API_BASE_URL, api, errorMessage } from "../api/client";

type CheckState = "idle" | "checking" | "healthy" | "ready" | "error";

export function BackendChecks() {
  const [health, setHealth] = useState<CheckState>("idle");
  const [readiness, setReadiness] = useState<CheckState>("idle");
  const [message, setMessage] = useState("");

  async function runChecks() {
    setHealth("checking");
    setReadiness("checking");
    setMessage("");

    const [healthResult, readyResult] = await Promise.allSettled([api.health(), api.ready()]);
    setHealth(
      healthResult.status === "fulfilled" && healthResult.value.status === "ok"
        ? "healthy"
        : "error"
    );
    setReadiness(
      readyResult.status === "fulfilled" && readyResult.value.status === "ready"
        ? "ready"
        : "error"
    );

    const failure = healthResult.status === "rejected"
      ? healthResult.reason
      : readyResult.status === "rejected"
        ? readyResult.reason
        : null;
    if (failure) setMessage(errorMessage(failure));
  }

  useEffect(() => {
    void runChecks();
  }, []);

  return (
    <section className="connection-card" aria-label="Backend connection">
      <div>
        <p className="eyebrow">Backend connection</p>
        <strong>{API_BASE_URL || "Local Vite proxy"}</strong>
      </div>
      <div className="check-row">
        <span className={"check-pill " + health}>Health: {health}</span>
        <span className={"check-pill " + readiness}>Ready: {readiness}</span>
        <button className="button button-quiet" type="button" onClick={() => void runChecks()}>
          Recheck
        </button>
      </div>
      {message && <p className="inline-error">{message}</p>}
    </section>
  );
}
