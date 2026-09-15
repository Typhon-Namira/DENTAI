import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Globe2 } from "lucide-react";

import "./arevik-cofounder.css";

type Lang = "en" | "hy" | "ru";

const COPY = {
  en: {
    role: "Co-Founder · Growth / International Relations",
    focus: "Growth & international partnerships",
    body:
      "Arevik Arzoyan leads Teta2's growth strategy, international partnerships, and engagement with public-sector and government stakeholders.",
  },
  hy: {
    role: "Համահիմնադիր · աճ / միջազգային կապեր",
    focus: "Աճ և միջազգային գործընկերություններ",
    body:
      "Arevik Arzoyan-ը ղեկավարում է Teta2-ի աճի ռազմավարությունը, միջազգային գործընկերությունները և պետական ու հանրային կառույցների հետ հարաբերությունները։",
  },
  ru: {
    role: "Сооснователь · рост / международные связи",
    focus: "Рост и международные партнерства",
    body:
      "Arevik Arzoyan отвечает за стратегию роста Teta2, международные партнерства и взаимодействие с государственными и общественными организациями.",
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
      <div className="deck2-person-head">
        <span>AA</span>
        <div>
          <small>{copy.role}</small>
          <h3>Arevik Arzoyan</h3>
        </div>
      </div>
      <div className="deck2-tech-focus teta2-arevik-focus">
        <Globe2 />
        <strong>{copy.focus}</strong>
        <p>{copy.body}</p>
      </div>
    </article>,
    host,
  );
}
