import { useEffect } from "react";

type Lang = "en" | "hy" | "ru";

type SeoEntry = {
  title: string;
  description: string;
  keywords: string;
};

const BASE = "https://teta2.com";
const LOGO = `${BASE}/images/teta2_logo_transparent.png`;

const SEO: Record<string, Record<Lang, SeoEntry>> = {
  "/": {
    en: { title: "Teta2 | AI-assisted OPG Intelligence & Patient Follow-up", description: "Teta2 is a dental clinical workflow for AI-assisted OPG review, clinician-confirmed possible findings, patient records and visible follow-up.", keywords: "Teta2, dental AI, OPG AI, panoramic dental x-ray, patient follow-up, dental clinic software" },
    hy: { title: "Teta2 | AI-ով OPG վերլուծություն և պացիենտի follow-up", description: "Teta2-ը dental clinical workflow է՝ AI-assisted OPG review-ի, բժշկի review-ի, patient record-ի և տեսանելի follow-up-ի համար։", keywords: "Teta2, dental AI, OPG, ատամնաբուժական AI, պանորամիկ ռենտգեն, follow-up" },
    ru: { title: "Teta2 | AI-анализ OPG и follow-up пациентов", description: "Teta2 — клинический dental workflow для AI-assisted review OPG, review врача, карты пациента и follow-up.", keywords: "Teta2, dental AI, OPG AI, панорамный снимок, стоматология, follow-up пациентов" },
  },
  "/product": {
    en: { title: "Teta2 Product | OPG AI, Patient Record & Follow-up Workflow", description: "Explore Teta2's focused product architecture: OPG history, AI-assisted possible findings, clinician review, smart patient records and patient-specific follow-up.", keywords: "Teta2 product, OPG AI software, dental patient record, dental follow-up software, panoramic x-ray workflow" },
    hy: { title: "Teta2 Product | OPG AI, patient record և follow-up", description: "Teta2 product architecture՝ OPG history, AI-assisted findings, clinician review, patient record և follow-up workflow։", keywords: "Teta2 product, OPG AI, dental software Armenia, patient record" },
    ru: { title: "Teta2 Product | OPG AI, карта пациента и follow-up", description: "Архитектура Teta2: история OPG, AI-assisted findings, review врача, карта пациента и follow-up workflow.", keywords: "Teta2 product, OPG AI, dental software, карта пациента, follow-up" },
  },
  "/how-it-works": {
    en: { title: "How Teta2 Works | OPG → Clinician Review → Patient Follow-up", description: "See how Teta2 carries an OPG through AI-assisted analysis, dentist review, patient record, follow-up timing, messaging and return tracking.", keywords: "how Teta2 works, OPG workflow, dental AI workflow, dentist review, patient recall, dental follow-up" },
    hy: { title: "Ինչպես է աշխատում Teta2 | OPG-ից դեպի follow-up", description: "Տեսեք Teta2 workflow-ը՝ OPG upload, AI-assisted analysis, dentist review, patient record, follow-up և messaging։", keywords: "Teta2 workflow, OPG AI, dentist review, follow-up" },
    ru: { title: "Как работает Teta2 | OPG → review врача → follow-up", description: "Workflow Teta2: OPG, AI-assisted analysis, review стоматолога, patient record, follow-up, сообщения и возврат пациента.", keywords: "Teta2 workflow, OPG AI, стоматологический AI, follow-up" },
  },
  "/pricing": {
    en: { title: "Teta2 Pricing | Dental OPG AI & Follow-up Subscription", description: "Review the currently displayed Teta2 clinic subscription, included OPG workflow, follow-up features, fair-use approach and access process.", keywords: "Teta2 pricing, dental AI pricing, OPG AI subscription, dental clinic software pricing" },
    hy: { title: "Teta2 Pricing | Dental OPG AI subscription", description: "Teta2 clinic subscription-ի, OPG workflow-ի, follow-up features-ի և access process-ի ընթացիկ նկարագրությունը։", keywords: "Teta2 pricing, dental AI Armenia, OPG subscription" },
    ru: { title: "Teta2 Pricing | Подписка на dental OPG AI", description: "Текущая подписка Teta2 для клиник, OPG workflow, follow-up функции, fair use и процесс доступа.", keywords: "Teta2 pricing, dental AI цена, OPG AI подписка" },
  },
  "/clinical-safety": {
    en: { title: "Teta2 Clinical Safety | Human-in-the-loop Dental AI", description: "Teta2 presents AI-assisted possible findings for dentist examination. Learn about clinical language, human oversight, imaging context and claim boundaries.", keywords: "Teta2 safety, dental AI safety, human in the loop, OPG AI clinical safety, dentist oversight" },
    hy: { title: "Teta2 Clinical Safety | Human-in-the-loop dental AI", description: "Teta2-ի clinical safety մոտեցումը՝ possible findings, dentist examination, human oversight և responsible claims։", keywords: "Teta2 safety, dental AI safety, dentist oversight" },
    ru: { title: "Teta2 Clinical Safety | Human-in-the-loop dental AI", description: "Clinical safety Teta2: possible findings, осмотр стоматолога, human oversight, imaging context и границы claims.", keywords: "Teta2 safety, dental AI safety, human oversight, OPG" },
  },
  "/about": {
    en: { title: "About Teta2 | Typhon Namira, Team & Contact in Yerevan", description: "Learn about Teta2, founder Typhon Namira, co-founder Van Arzoyan, the project's focused dental AI mission and contact details in Yerevan, Armenia.", keywords: "Teta2, Typhon Namira, Van Arzoyan, Teta2 founder, dental AI Yerevan, Armenia startup, Typhon Namira Teta2" },
    hy: { title: "Teta2-ի մասին | Typhon Namira, թիմ և կապ Երևանում", description: "Teta2 dental AI նախագիծը, founder Typhon Namira, co-founder Van Arzoyan և կապի տվյալները Երևանում։", keywords: "Teta2, Typhon Namira, Թայֆոն Նամիրա, Van Arzoyan, dental AI Armenia, Yerevan startup" },
    ru: { title: "О Teta2 | Typhon Namira, команда и контакты в Ереване", description: "Teta2, founder Typhon Namira, co-founder Van Arzoyan, dental AI проект и контакты в Ереване, Армения.", keywords: "Teta2, Typhon Namira, Тайфон Намира, Van Arzoyan, dental AI Armenia, Yerevan startup" },
  },
};

function getLang(): Lang {
  const value = localStorage.getItem("teta2-product-language") ?? localStorage.getItem("teta2-v4-language");
  return value === "hy" || value === "ru" ? value : "en";
}

function setMeta(name: string, content: string, property = false) {
  const selector = property ? `meta[property="${name}"]` : `meta[name="${name}"]`;
  let node = document.head.querySelector<HTMLMetaElement>(selector);
  if (!node) {
    node = document.createElement("meta");
    node.setAttribute(property ? "property" : "name", name);
    document.head.appendChild(node);
  }
  node.content = content;
}

function setLink(rel: string, href: string, hreflang?: string) {
  const selector = hreflang ? `link[rel="${rel}"][hreflang="${hreflang}"]` : `link[rel="${rel}"]:not([hreflang])`;
  let node = document.head.querySelector<HTMLLinkElement>(selector);
  if (!node) {
    node = document.createElement("link");
    node.rel = rel;
    if (hreflang) node.hreflang = hreflang;
    document.head.appendChild(node);
  }
  node.href = href;
}

function personJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "Person",
    "@id": `${BASE}/about#typhon-namira`,
    name: "Typhon Namira",
    url: `${BASE}/about#typhon-namira`,
    sameAs: ["https://ru.linkedin.com/in/typhon-namira", "https://pulsemealx.com/aboutUs.html"],
    jobTitle: "Founder",
    worksFor: { "@id": `${BASE}/#organization` },
  };
}

function organizationJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    "@id": `${BASE}/#organization`,
    name: "Teta2",
    url: BASE,
    logo: LOGO,
    founder: { "@id": `${BASE}/about#typhon-namira` },
    email: "teta2support@gmail.com",
    telephone: "+37493700251",
    address: {
      "@type": "PostalAddress",
      streetAddress: "4 Arshakunyats Avenue",
      addressLocality: "Yerevan",
      addressCountry: "AM",
    },
    description: "Dental software project for AI-assisted OPG review, clinician-controlled findings, patient records and follow-up workflow.",
  };
}

function websiteJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": `${BASE}/#website`,
    url: BASE,
    name: "Teta2",
    publisher: { "@id": `${BASE}/#organization` },
  };
}

function applyStructuredData() {
  document.querySelectorAll('script[data-teta2-seo="true"]').forEach(node => node.remove());
  [organizationJsonLd(), personJsonLd(), websiteJsonLd()].forEach(data => {
    const node = document.createElement("script");
    node.type = "application/ld+json";
    node.dataset.teta2Seo = "true";
    node.textContent = JSON.stringify(data);
    document.head.appendChild(node);
  });
}

export function PublicSeo() {
  useEffect(() => {
    const apply = () => {
      const path = window.location.pathname;
      const lang = getLang();
      const entry = SEO[path]?.[lang] ?? SEO["/"][lang];
      const canonical = `${BASE}${path === "/" ? "/" : path}`;
      document.title = entry.title;
      document.documentElement.lang = lang;
      setMeta("description", entry.description);
      setMeta("keywords", entry.keywords);
      setMeta("robots", "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1");
      setMeta("author", "Teta2");
      setMeta("og:type", "website", true);
      setMeta("og:site_name", "Teta2", true);
      setMeta("og:title", entry.title, true);
      setMeta("og:description", entry.description, true);
      setMeta("og:url", canonical, true);
      setMeta("og:image", LOGO, true);
      setMeta("twitter:card", "summary");
      setMeta("twitter:title", entry.title);
      setMeta("twitter:description", entry.description);
      setMeta("twitter:image", LOGO);
      setLink("canonical", canonical);
      applyStructuredData();
    };
    apply();
    const route = () => apply();
    const language = () => apply();
    window.addEventListener("popstate", route);
    window.addEventListener("teta2-language-change", language);
    return () => {
      window.removeEventListener("popstate", route);
      window.removeEventListener("teta2-language-change", language);
    };
  }, []);
  return null;
}
