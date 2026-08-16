import { useState, type FormEvent } from "react";
import { api, clearSession, errorMessage } from "../api/client";
import type { CurrentUser } from "../api/types";

interface LoginCardProps {
  onAuthenticated: (user: CurrentUser) => void;
}

export function LoginCard({ onAuthenticated }: LoginCardProps) {
  const [clinicSlug, setClinicSlug] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      await api.login({
        clinic_slug: clinicSlug.trim(),
        identifier: identifier.trim(),
        password
      });
      setPassword("");
      const user = await api.me();
      onAuthenticated(user);
    } catch (reason) {
      clearSession();
      setPassword("");
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-copy">
        <span className="brand-mark" aria-hidden="true">D</span>
        <p className="eyebrow">Internal product test</p>
        <h1>Clinical AI, tested in the real workflow.</h1>
        <p>
          Connect to DENTAI, choose an authorized patient, upload an OPG image,
          and follow the V5 analysis through clinician review.
        </p>
        <div className="safety-note">
          AI-assisted clinical decision support. Findings require clinician review.
        </div>
      </section>

      <section className="card login-card">
        <div>
          <p className="eyebrow">Secure access</p>
          <h2>Sign in to your clinic</h2>
          <p className="muted">Credentials are sent only to the configured DENTAI API.</p>
        </div>
        <form onSubmit={submit}>
          <label>
            Clinic slug
            <input
              autoComplete="organization"
              minLength={2}
              maxLength={80}
              pattern="[a-z0-9-]+"
              required
              value={clinicSlug}
              onChange={(event) => setClinicSlug(event.target.value.toLowerCase())}
              placeholder="clinic-name"
            />
          </label>
          <label>
            Email or username
            <input
              autoComplete="username"
              minLength={2}
              maxLength={320}
              required
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              placeholder="doctor@clinic.example"
            />
          </label>
          <label>
            Password
            <input
              autoComplete="current-password"
              type="password"
              minLength={8}
              maxLength={256}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error && <div className="error-panel" role="alert">{error}</div>}
          <button className="button button-primary button-wide" disabled={busy} type="submit">
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
