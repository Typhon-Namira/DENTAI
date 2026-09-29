import { Mail, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { API_BASE_URL } from "../api/client";
import "./verified-sales-managers.css";

type PublicManager = {
  id: string;
  full_name: string;
  title: string;
  email: string;
  phone?: string | null;
  territory?: string | null;
  bio?: string | null;
  photo_available: boolean;
  verified: boolean;
};

export function VerifiedSalesManagers() {
  const [managers, setManagers] = useState<PublicManager[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/api/v1/platform/sales/public/managers`)
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load verified managers");
        return response.json() as Promise<PublicManager[]>;
      })
      .then((rows) => { if (!cancelled) setManagers(rows.filter((row) => row.verified)); })
      .catch(() => { if (!cancelled) setManagers([]); });
    return () => { cancelled = true; };
  }, []);

  if (!managers.length) return null;

  return <section className="verified-sales-section">
    <header>
      <span>VERIFIED SALES TEAM</span>
      <h2>Our approved Teta2 sales managers</h2>
      <p>These profiles are generated directly from active manager accounts approved by Teta2 administration.</p>
    </header>
    <div className="verified-sales-grid">
      {managers.map((manager) => <article className="verified-sales-card" key={manager.id}>
        <div className="verified-sales-photo">
          {manager.photo_available
            ? <img src={`${API_BASE_URL}/api/v1/platform/sales/public/managers/${manager.id}/photo`} alt={manager.full_name} />
            : <div className="verified-sales-placeholder" aria-label={manager.full_name}>{manager.full_name.split(/\s+/).map((part) => part[0]).join("").slice(0,2).toUpperCase()}</div>}
          <div className="verified-sales-ribbon"><ShieldCheck /> VERIFIED</div>
        </div>
        <div className="verified-sales-body">
          <small>{manager.territory || "Teta2 Sales"}</small>
          <h3>{manager.full_name}</h3>
          <strong>{manager.title}</strong>
          {manager.bio && <p>{manager.bio}</p>}
          <a href={`mailto:${manager.email}`}><Mail /> {manager.email}</a>
        </div>
      </article>)}
    </div>
  </section>;
}
