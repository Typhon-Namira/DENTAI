import { useEffect } from "react";

import {
  localizedPublicPath,
  parseLocalizedPublicPath,
  publicAlternateUrls,
  type SeoPublicLanguage,
  type SeoPublicPath,
} from "./publicLocaleRouting";

type SeoEntry = {
  title: string;
  description: string;
  keywords: string;
};

const BASE = "https://www.teta2.com";
const LOGO = `${BASE}/images/teta2_logo_transparent.png`;

const SEO: Record<SeoPublicPath, Record<SeoPublicLanguage, SeoEntry>> = {
  "/": {
    en: {
      title: "Dental AI Software for OPG & Panoramic X-Rays | Teta2",
      description: "Teta2 is dental AI software for clinics: AI-assisted OPG and panoramic dental X-ray review, clinician-controlled findings, patient records, follow-up and booking.",
      keywords: "dental AI software, dental x-ray AI software, OPG AI, panoramic dental x-ray AI, AI dental x-ray analysis, dental clinic software, patient follow-up software",
    },
    hy: {
      title: "Ատամնաբուժական AI՝ պանորամիկ ռենտգենի վերլուծության համար | Teta2",
      description: "Teta2-ը ատամնաբուժական կլինիկաների համար AI ծրագիր է՝ OPG և պանորամիկ ռենտգենային պատկերների AI-աջակցվող վերլուծության, բժշկի վերանայման, պացիենտի քարտի, հետագա վերահսկման և ամրագրման համար։",
      keywords: "ատամնաբուժական AI, արհեստական բանականություն ատամնաբուժությունում, պանորամիկ ռենտգեն, պանորամիկ ռենտգենային հետազոտություն, OPG վերլուծություն, ատամնաբուժական կլինիկայի ծրագիր",
    },
    ru: {
      title: "ИИ для стоматологии: анализ ОПТГ и панорамных снимков | Teta2",
      description: "Teta2 — программа с ИИ для стоматологических клиник: анализ ОПТГ и панорамных снимков зубов, проверка врачом, карта пациента, последующее наблюдение и запись на прием.",
      keywords: "ИИ для стоматологии, искусственный интеллект в стоматологии, анализ ОПТГ, анализ панорамного снимка зубов, стоматологическая программа, программа для стоматологии",
    },
  },
  "/product": {
    en: {
      title: "Dental AI OPG Software for Clinics | Teta2",
      description: "Explore Teta2 dental AI software for panoramic X-ray and OPG review, tooth-level clinician decisions, patient records, multilingual follow-up, WhatsApp outreach and booking.",
      keywords: "dental AI OPG software, panoramic x-ray analysis software, dental x-ray AI, dental clinic software, patient recall software, dental follow-up software",
    },
    hy: {
      title: "Ատամնաբուժական AI ծրագիր՝ OPG-ի վերլուծության համար | Teta2",
      description: "Teta2-ը միավորում է պանորամիկ ռենտգենի և OPG-ի AI-աջակցվող վերլուծությունը, բժշկի՝ ատամ առ ատամ վերանայումը, պացիենտի քարտը, WhatsApp հետագա կապը և ամրագրումը։",
      keywords: "OPG AI ծրագիր, պանորամիկ ռենտգեն AI, ատամնաբուժական ծրագիր Հայաստան, ատամնաբուժական կլինիկայի ծրագիր, պացիենտի հետագա վերահսկում",
    },
    ru: {
      title: "ИИ-анализ ОПТГ для стоматологических клиник | Teta2",
      description: "Teta2 объединяет ИИ-анализ ОПТГ и панорамных снимков, проверку каждого зуба врачом, карту пациента, WhatsApp-наблюдение и запись на прием в одном процессе.",
      keywords: "ИИ анализ ОПТГ, анализ панорамного снимка зубов, программа для стоматологической клиники, стоматологический ИИ, карта пациента, контроль пациентов",
    },
  },
  "/how-it-works": {
    en: {
      title: "AI Dental X-Ray Analysis Workflow | Teta2",
      description: "See how Teta2 moves a panoramic dental X-ray or OPG from AI-assisted analysis to dentist review, patient record, tooth-by-tooth follow-up, messaging and appointment booking.",
      keywords: "AI dental x-ray analysis, dental x-ray AI workflow, OPG analysis software, panoramic radiograph AI, dentist review workflow, patient follow-up",
    },
    hy: {
      title: "Ինչպես է աշխատում OPG-ի AI վերլուծությունը | Teta2",
      description: "Տեսեք Teta2-ի գործընթացը՝ պանորամիկ ռենտգեն կամ OPG, AI-աջակցվող վերլուծություն, ատամնաբույժի վերանայում, պացիենտի քարտ, ատամ առ ատամ հետագա վերահսկում և ամրագրում։",
      keywords: "OPG AI վերլուծություն, պանորամիկ ռենտգեն վերլուծություն, ատամնաբուժական AI, պացիենտի հետագա վերահսկում, ատամնաբույժի վերանայում",
    },
    ru: {
      title: "Как работает ИИ-анализ ОПТГ в Teta2",
      description: "Как Teta2 обрабатывает ОПТГ и панорамные снимки зубов: ИИ-анализ, проверка стоматологом, карта пациента, наблюдение по каждому зубу, сообщения и запись на прием.",
      keywords: "как работает ИИ в стоматологии, ИИ анализ ОПТГ, анализ панорамного снимка, стоматологический ИИ, наблюдение пациентов",
    },
  },
  "/pricing": {
    en: {
      title: "Dental AI Software Pricing for Clinics | Teta2",
      description: "View Teta2 dental AI software pricing for clinics in Armenia and Russia, including OPG review, patient records, clinician-controlled follow-up and clinic access terms.",
      keywords: "dental AI software pricing, OPG AI pricing, dental clinic software pricing, dental x-ray AI subscription, Teta2 pricing",
    },
    hy: {
      title: "Teta2 գներ | AI ծրագիր ատամնաբուժական կլինիկաների համար",
      description: "Teta2-ի ամսական գները Հայաստանի և Ռուսաստանի ատամնաբուժական կլինիկաների համար՝ OPG վերլուծություն, պացիենտի քարտ, բժշկի վերահսկմամբ հետագա կապ և ամրագրում։",
      keywords: "Teta2 գներ, ատամնաբուժական AI գին, OPG AI գին, ատամնաբուժական ծրագիր գին, կլինիկայի բաժանորդագրություն",
    },
    ru: {
      title: "Цена Teta2 | ИИ для стоматологической клиники",
      description: "Стоимость Teta2 для клиник Армении и России: ИИ-анализ ОПТГ, карта пациента, наблюдение под контролем врача и запись на прием в рамках подписки.",
      keywords: "Teta2 цена, ИИ для стоматологии цена, анализ ОПТГ цена, программа для стоматологии цена, подписка стоматологическая программа",
    },
  },
  "/clinical-safety": {
    en: {
      title: "Dental AI Safety & Clinician Review | Teta2",
      description: "Learn how Teta2 keeps dentists in control of AI-assisted OPG and panoramic X-ray findings, clinical review, patient communication, follow-up and care decisions.",
      keywords: "dental AI safety, clinician review dental AI, human in the loop dental AI, OPG AI safety, panoramic x-ray AI safety",
    },
    hy: {
      title: "AI-ի անվտանգ կիրառում ատամնաբուժությունում | Teta2",
      description: "Իմացեք, թե ինչպես է Teta2-ը պահում ատամնաբույժին OPG և պանորամիկ ռենտգենի AI արդյունքների, կլինիկական վերանայման, պացիենտի հաղորդակցության և հետագա որոշումների վերահսկողության կենտրոնում։",
      keywords: "AI անվտանգություն ատամնաբուժությունում, ատամնաբուժական AI, OPG AI անվտանգություն, բժշկի վերահսկում, պանորամիկ ռենտգեն AI",
    },
    ru: {
      title: "Безопасность ИИ в стоматологии | Teta2",
      description: "Teta2 сохраняет контроль стоматолога над ИИ-анализом ОПТГ и панорамных снимков, проверкой результатов, сообщениями пациентам и решениями по наблюдению.",
      keywords: "безопасность ИИ в стоматологии, стоматологический ИИ, ИИ анализ ОПТГ, контроль врача, искусственный интеллект стоматология",
    },
  },
  "/about": {
    en: {
      title: "Teta2 Dental AI Software | Team in Yerevan, Armenia",
      description: "Meet the team building Teta2, a dental AI software project in Yerevan focused on panoramic X-ray and OPG review, patient records and clinician-controlled follow-up.",
      keywords: "Teta2, dental AI Armenia, dental AI Yerevan, Typhon Namira, Van Arzoyan, dental software startup Armenia",
    },
    hy: {
      title: "Teta2-ի մասին | Ատամնաբուժական AI նախագիծ Երևանում",
      description: "Ծանոթացեք Երևանում ստեղծվող Teta2 ատամնաբուժական AI նախագծի թիմին, որը կենտրոնացած է OPG և պանորամիկ ռենտգենի վերլուծության, պացիենտի քարտի և բժշկի վերահսկմամբ հետագա աշխատանքի վրա։",
      keywords: "Teta2, ատամնաբուժական AI Հայաստան, ատամնաբուժական AI Երևան, Typhon Namira, Van Arzoyan, տեխնոլոգիական ստարտափ Հայաստան",
    },
    ru: {
      title: "О Teta2 | Стоматологический ИИ из Еревана",
      description: "Команда Teta2 в Ереване создает стоматологическое ПО с ИИ для анализа ОПТГ и панорамных снимков, ведения карт пациентов и последующего наблюдения под контролем врача.",
      keywords: "Teta2, стоматологический ИИ Армения, стоматологический ИИ Ереван, Typhon Namira, Van Arzoyan, стоматологическое ПО",
    },
  },
};

const OG_LOCALE: Record<SeoPublicLanguage, string> = {
  en: "en_US",
  hy: "hy_AM",
  ru: "ru_RU",
};

function storedLanguage(): SeoPublicLanguage {
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

function setCanonical(href: string) {
  let node = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  if (!node) {
    node = document.createElement("link");
    node.rel = "canonical";
    document.head.appendChild(node);
  }
  node.href = href;
}

function setHreflang(basePath: SeoPublicPath) {
  document.head.querySelectorAll('link[data-teta2-hreflang="true"]').forEach((node) => node.remove());
  const alternates = publicAlternateUrls(BASE, basePath);
  (["en", "hy", "ru", "x-default"] as const).forEach((hreflang) => {
    const node = document.createElement("link");
    node.rel = "alternate";
    node.hreflang = hreflang;
    node.href = alternates[hreflang];
    node.dataset.teta2Hreflang = "true";
    document.head.appendChild(node);
  });
}

function clearHreflang() {
  document.head.querySelectorAll('link[data-teta2-hreflang="true"]').forEach((node) => node.remove());
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
    description: "Dental AI software project for AI-assisted OPG and panoramic X-ray review, clinician-controlled findings, patient records and follow-up workflow.",
  };
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

function webpageJsonLd(canonical: string, language: SeoPublicLanguage, entry: SeoEntry) {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    "@id": `${canonical}#webpage`,
    url: canonical,
    name: entry.title,
    description: entry.description,
    inLanguage: language,
    keywords: entry.keywords,
    isPartOf: { "@id": `${BASE}/#website` },
    about: { "@id": `${BASE}/#organization` },
  };
}

function softwareJsonLd(language: SeoPublicLanguage) {
  const names: Record<SeoPublicLanguage, string> = {
    en: "Teta2 dental AI software",
    hy: "Teta2 ատամնաբուժական AI ծրագիր",
    ru: "Teta2 — ИИ для стоматологии",
  };
  const descriptions: Record<SeoPublicLanguage, string> = {
    en: "Web software for dental clinics that connects AI-assisted OPG and panoramic X-ray review with clinician decisions, patient follow-up and booking.",
    hy: "Վեբ ծրագիր ատամնաբուժական կլինիկաների համար, որը կապում է OPG և պանորամիկ ռենտգենի AI-աջակցվող վերլուծությունը բժշկի որոշումների, պացիենտի հետագա վերահսկման և ամրագրման հետ։",
    ru: "Веб-программа для стоматологических клиник, объединяющая ИИ-анализ ОПТГ и панорамных снимков с решениями врача, наблюдением пациента и записью на прием.",
  };
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "@id": `${BASE}/product#software`,
    name: names[language],
    url: `${BASE}${localizedPublicPath("/product", language)}`,
    applicationCategory: "BusinessApplication",
    applicationSubCategory: "Dental clinic software",
    operatingSystem: "Web",
    description: descriptions[language],
    publisher: { "@id": `${BASE}/#organization` },
    audience: { "@type": "Audience", audienceType: "Dental clinics and dental professionals" },
    featureList: [
      "AI-assisted OPG and panoramic dental X-ray review",
      "Tooth-level clinician review",
      "Patient records and OPG history",
      "Sequential patient follow-up",
      "Multilingual patient messaging",
      "Appointment booking workflow",
    ],
  };
}

function breadcrumbJsonLd(basePath: SeoPublicPath, canonical: string, entry: SeoEntry) {
  if (basePath === "/") return null;
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Teta2", item: `${BASE}/` },
      { "@type": "ListItem", position: 2, name: entry.title.split("|")[0].trim(), item: canonical },
    ],
  };
}

function applyStructuredData(basePath: SeoPublicPath, canonical: string, language: SeoPublicLanguage, entry: SeoEntry) {
  document.querySelectorAll('script[data-teta2-seo="true"]').forEach((node) => node.remove());
  const data: object[] = [organizationJsonLd(), websiteJsonLd(), webpageJsonLd(canonical, language, entry)];
  if (basePath === "/" || basePath === "/product" || basePath === "/pricing") data.push(softwareJsonLd(language));
  if (basePath === "/about") data.push(personJsonLd());
  const breadcrumb = breadcrumbJsonLd(basePath, canonical, entry);
  if (breadcrumb) data.push(breadcrumb);
  data.forEach((item) => {
    const node = document.createElement("script");
    node.type = "application/ld+json";
    node.dataset.teta2Seo = "true";
    node.textContent = JSON.stringify(item);
    document.head.appendChild(node);
  });
}

function clearStructuredData() {
  document.querySelectorAll('script[data-teta2-seo="true"]').forEach((node) => node.remove());
}

function applySeo() {
  const parsed = parseLocalizedPublicPath(window.location.pathname);
  const indexable = parsed !== null;

  if (!indexable) {
    const language = storedLanguage();
    const current = `${BASE}${window.location.pathname || "/"}`;
    document.documentElement.lang = language;
    document.title = window.location.pathname === "/login" ? "Teta2 | Clinic Sign In" : "Teta2 | Clinical Platform";
    setMeta("description", "Secure Teta2 clinical platform access for authorized dental-clinic users.");
    setMeta("keywords", "Teta2");
    setMeta("robots", "noindex,nofollow,noarchive");
    setMeta("author", "Teta2");
    setMeta("og:type", "website", true);
    setMeta("og:site_name", "Teta2", true);
    setMeta("og:title", "Teta2 Clinical Platform", true);
    setMeta("og:description", "Secure Teta2 clinical platform access.", true);
    setMeta("og:url", current, true);
    setMeta("og:image", LOGO, true);
    setMeta("twitter:card", "summary");
    setMeta("twitter:title", "Teta2 Clinical Platform");
    setMeta("twitter:description", "Secure Teta2 clinical platform access.");
    setMeta("twitter:image", LOGO);
    setCanonical(current);
    clearHreflang();
    clearStructuredData();
    return;
  }

  const { basePath, language } = parsed;
  const entry = SEO[basePath][language];
  const canonical = `${BASE}${localizedPublicPath(basePath, language)}`;

  document.documentElement.lang = language;
  document.title = entry.title;
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
  setMeta("og:locale", OG_LOCALE[language], true);
  setMeta("twitter:card", "summary");
  setMeta("twitter:title", entry.title);
  setMeta("twitter:description", entry.description);
  setMeta("twitter:image", LOGO);
  setCanonical(canonical);
  setHreflang(basePath);
  applyStructuredData(basePath, canonical, language, entry);
}

export function PublicSeo() {
  useEffect(() => {
    const applyAfterRouteSettles = () => {
      applySeo();
      window.setTimeout(applySeo, 0);
    };

    applyAfterRouteSettles();
    window.addEventListener("popstate", applyAfterRouteSettles);
    window.addEventListener("teta2-language-change", applyAfterRouteSettles);
    window.addEventListener("teta2-localized-route", applyAfterRouteSettles);

    return () => {
      window.removeEventListener("popstate", applyAfterRouteSettles);
      window.removeEventListener("teta2-language-change", applyAfterRouteSettles);
      window.removeEventListener("teta2-localized-route", applyAfterRouteSettles);
    };
  }, []);

  return null;
}
