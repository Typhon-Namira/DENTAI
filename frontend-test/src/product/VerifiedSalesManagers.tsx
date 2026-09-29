import { BadgeCheck, Mail } from "lucide-react";
import { useEffect, useState } from "react";

import { API_BASE_URL } from "../api/client";
import "./verified-sales-managers.css";

type Lang = "en" | "hy" | "ru";

type PublicManager = {
  id: string;
  name: string;
  title: string;
  email: string;
  photo_url: string;
  verified: boolean;
};

const COPY = {
  en: {
    kicker: "Verified sales team",
    title: "Official Teta2 sales managers",
    lead: "These managers are verified by Teta2 platform administration.",
    verified: "VERIFIED",
  },
  hy: {
    kicker: "Հաստատված վաճառքի թիմ",
    title: "Teta2-ի պաշտոնական վաճառքի ղեկավարներ",
    lead: "Այս ղեկավարները հաստատված են Teta2 հարթակի ադմինիստրացիայի կողմից։",
    verified: "VERIFIED",
  },
  ru: {
    kicker: "Проверенная команда продаж",
    title: "Официальные менеджеры по продажам Teta2",
    lead: "Эти менеджеры подтверждены администрацией платформы Teta2.",
    verified: "VERIFIED",
  },
} as const;

export function VerifiedSalesManagers({ lang }: { lang: Lang }) {
  const [rows, setRows] = useState<PublicManager[]>([]);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/api/v1/platform/sales-managers/public`)
      .then(async (response) => {
        if (!response.ok) return [];
        return await response.json() as PublicManager[];
      })
      .then((data) => {
        if (active) setRows(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        if (active) setRows([]);
      });
    return () => { active = false; };
  }, []);

  if (!rows.length) return null;
  const copy = COPY[lang];

  return <section className="vsm-section" aria-label={copy.title}>
    <header className="vsm-heading">
      <span>{copy.kicker}</span>
      <h3>{copy.title}</h3>
      <p>{copy.lead}</p>
    </header>
    <div className="vsm-grid">
      {rows.map((manager) => <article className="vsm-card" key={manager.id}>
        <div className="vsm-photo-wrap">
          <img src={`${API_BASE_URL}${manager.photo_url}`} alt={manager.name} loading="lazy"/>
          <div className="vsm-ribbon"><BadgeCheck/>{copy.verified}</div>
        </div>
        <div className="vsm-card-body">
          <small>{manager.title}</small>
          <h4>{manager.name}</h4>
          <a href={`mailto:${manager.email}`}><Mail/>{manager.email}</a>
        </div>
      </article>)}
    </div>
  </section>;
}
