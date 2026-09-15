import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Globe2, Landmark, TrendingUp } from "lucide-react";

import "./arevik-cofounder.css";

type Lang = "en" | "hy" | "ru";

const COPY = {
  en: {
    role: "Co-Founder · Growth, International Relations & Public-Sector Partnerships",
    body:
      "Arevik Arzoyan leads Teta2's growth strategy, international partnerships, and engagement with public institutions and government stakeholders as the company expands across markets.",
    growth: "Growth strategy",
    international: "International partnerships",
    publicSector: "Public-sector relations",
    alt: "Arevik Arzoyan, Co-Founder of Teta2",
  },
  hy: {
    role: "Համահիմնադիր · աճի ռազմավարություն, միջազգային կապեր և պետական հատվածի գործընկերություններ",
    body:
      "Arevik Arzoyan-ը ղեկավարում է Teta2-ի աճի ռազմավարությունը, միջազգային գործընկերությունների զարգացումը և պետական ու ինստիտուցիոնալ կառույցների հետ հարաբերությունները՝ նոր շուկաներում ընդլայնման համար։",
    growth: "Աճի ռազմավարություն",
    international: "Միջազգային գործընկերություններ",
    publicSector: "Պետական հատվածի կապեր",
    alt: "Arevik Arzoyan՝ Teta2-ի համահիմնադիր",
  },
  ru: {
    role: "Сооснователь · стратегия роста, международные связи и партнерства с государственным сектором",
    body:
      "Arevik Arzoyan отвечает за стратегию роста Teta2, развитие международных партнерств и взаимодействие с государственными и институциональными организациями при выходе на новые рынки.",
    growth: "Стратегия роста",
    international: "Международные партнерства",
    publicSector: "Связи с государственным сектором",
    alt: "Arevik Arzoyan, сооснователь Teta2",
  },
} as const;

function languageNow(): Lang {
  const value =
    localStorage.getItem("teta2-product-language") ??
    localStorage.getItem("teta2-v4-language");
  return value === "hy" || value === "ru" ? value : "en";
}

export function ArevikCofounder() {
  const [host, setHost] = useState<HTMLElement | null>(null);
  const [lang, setLang] = useState<Lang>(() => languageNow());
  const [route, setRoute] = useState(window.location.pathname);

  useEffect(() => {
    const onRoute = () => setRoute(window.location.pathname);
    const onLanguage = () => setLang(languageNow());
    window.addEventListener("popstate", onRoute);
    window.addEventListener("teta2-language-change", onLanguage);
    window.addEventListener("storage", onLanguage);
    return () => {
      window.removeEventListener("popstate", onRoute);
      window.removeEventListener("teta2-language-change", onLanguage);
      window.removeEventListener("storage", onLanguage);
    };
  }, []);

  useEffect(() => {
    if (route !== "/about") {
      setHost(null);
      return;
    }

    let observer: MutationObserver | null = null;
    let frame = 0;

    const findTeam = () => {
      const next = document.querySelector<HTMLElement>(".deck2-about .deck2-team");
      if (next) {
        setHost((current) => (current === next ? current : next));
        observer?.disconnect();
        observer = null;
        return true;
      }
      return false;
    };

    frame = window.requestAnimationFrame(() => {
      if (findTeam()) return;
      observer = new MutationObserver(() => {
        findTeam();
      });
      observer.observe(document.body, { childList: true, subtree: true });
    });

    return () => {
      window.cancelAnimationFrame(frame);
      observer?.disconnect();
    };
  }, [route]);

  if (!host) return null;

  const copy = COPY[lang];

  return createPortal(
    <article id="arevik-arzoyan" className="teta2-arevik-card">
      <div className="teta2-arevik-photo">
        <img
          src="/images/IMG_8898.jpg"
          alt={copy.alt}
          loading="lazy"
          decoding="async"
        />
      </div>
      <div className="teta2-arevik-content">
        <div className="deck2-person-head teta2-arevik-head">
          <span>AA</span>
          <div>
            <small>{copy.role}</small>
            <h3>Arevik Arzoyan</h3>
          </div>
        </div>
        <p className="teta2-arevik-body">{copy.body}</p>
        <div className="teta2-arevik-focus" aria-label={copy.role}>
          <span><TrendingUp />{copy.growth}</span>
          <span><Globe2 />{copy.international}</span>
          <span><Landmark />{copy.publicSector}</span>
        </div>
      </div>
    </article>,
    host,
  );
}
