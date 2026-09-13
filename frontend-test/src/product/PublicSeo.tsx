import { useEffect } from "react";

type Lang = "en" | "hy" | "ru";

type SeoEntry = {
  title: string;
  description: string;
  keywords: string;
};

const BASE = "https://www.teta2.com";
const LOGO = `${BASE}/images/teta2_logo_transparent.png`;
const INDEXABLE_PATHS = new Set([
  "/",
  "/product",
  "/how-it-works",
  "/pricing",
  "/clinical-safety",
  "/about",
]);

const SEO: Record<string, Record<Lang, SeoEntry>> = {
  "/": {
    en: { title: "Teta2 | AI-assisted OPG Analysis & Patient Follow-up", description: "Teta2 helps dental clinics review OPG radiographs with AI-assisted possible findings, keep patient records organized, and manage clinician-controlled follow-up.", keywords: "Teta2, dental AI, OPG AI, panoramic dental x-ray, patient follow-up, dental clinic software" },
    hy: { title: "Teta2 | AI-աջակցվող OPG վերլուծություն և հետագա վերահսկում", description: "Teta2-ն օգնում է ատամնաբուժական կլինիկաներին AI-աջակցվող հնարավոր փոփոխություններով վերանայել OPG պատկերները, կազմակերպել պացիենտների քարտերը և կառավարել բժշկի վերահսկմամբ հետագա կապը։", keywords: "Teta2, ատամնաբուժական AI, OPG, պանորամիկ ռենտգեն, պացիենտի հետագա վերահսկում, ատամնաբուժական ծրագիր" },
    ru: { title: "Teta2 | Анализ OPG с ИИ и последующее наблюдение", description: "Teta2 помогает стоматологическим клиникам анализировать OPG с поддержкой ИИ, вести карты пациентов и управлять последующим наблюдением под контролем врача.", keywords: "Teta2, стоматологический ИИ, OPG AI, панорамный снимок, наблюдение пациентов, программа для стоматологии" },
  },
  "/product": {
    en: { title: "Teta2 Product | OPG AI, Patient Records & Follow-up", description: "Explore Teta2's dental workflow for OPG history, AI-assisted possible findings, clinician review, patient records, WhatsApp follow-up and return tracking.", keywords: "Teta2 product, OPG AI software, dental patient record, dental follow-up software, panoramic x-ray workflow" },
    hy: { title: "Teta2 արտադրանք | OPG AI, պացիենտի քարտ և վերահսկում", description: "Բացահայտեք Teta2-ի կլինիկական գործընթացը՝ OPG պատմություն, AI-աջակցվող հնարավոր փոփոխություններ, բժշկի վերանայում, պացիենտի քարտ և հետագա վերահսկում։", keywords: "Teta2, OPG AI, ատամնաբուժական ծրագիր Հայաստան, պացիենտի քարտ, հետագա վերահսկում" },
    ru: { title: "Teta2 | OPG AI, карта пациента и наблюдение", description: "Возможности Teta2: история OPG, возможные изменения с поддержкой ИИ, проверка врачом, карта пациента, WhatsApp-наблюдение и отслеживание возвращения.", keywords: "Teta2, OPG AI, стоматологическая программа, карта пациента, последующее наблюдение" },
  },
  "/how-it-works": {
    en: { title: "How Teta2 Works | OPG to Clinician Review & Follow-up", description: "See how Teta2 takes an OPG from AI-assisted analysis through dentist review, patient record, tooth-by-tooth follow-up, messaging and return tracking.", keywords: "how Teta2 works, OPG workflow, dental AI workflow, dentist review, patient recall, dental follow-up" },
    hy: { title: "Ինչպես է աշխատում Teta2 | OPG-ից մինչև վերահսկում", description: "Տեսեք Teta2-ի ամբողջ գործընթացը՝ OPG վերբեռնում, AI-աջակցվող վերլուծություն, ատամնաբույժի վերանայում, պացիենտի քարտ, ատամ առ ատամ վերահսկում և հաղորդագրություններ։", keywords: "Teta2, OPG AI, ատամնաբույժի վերանայում, հետագա վերահսկում, կլինիկական գործընթաց" },
    ru: { title: "Как работает Teta2 | От OPG до наблюдения пациента", description: "Посмотрите процесс Teta2: загрузка OPG, анализ с поддержкой ИИ, проверка стоматологом, карта пациента, наблюдение по каждому зубу и сообщения.", keywords: "Teta2, OPG AI, стоматологический ИИ, проверка врача, наблюдение пациента" },
  },
  "/pricing": {
    en: { title: "Teta2 Pricing | Dental OPG AI & Follow-up Subscription", description: "View Teta2 clinic subscription pricing for Armenia and Russia, included OPG workflow, follow-up features, fair-use policy and access process.", keywords: "Teta2 pricing, dental AI pricing, OPG AI subscription, dental clinic software pricing" },
    hy: { title: "Teta2 գներ | OPG AI և կլինիկայի բաժանորդագրություն", description: "Տեսեք Teta2-ի՝ Հայաստանի և Ռուսաստանի կլինիկաների բաժանորդագրության գները, OPG գործընթացը, հետագա վերահսկման գործառույթները և մուտքի կարգը։", keywords: "Teta2 գներ, dental AI Armenia, OPG բաժանորդագրություն, ատամնաբուժական ծրագիր" },
    ru: { title: "Цены Teta2 | Подписка на OPG AI для клиник", description: "Цены подписки Teta2 для клиник Армении и России, функции OPG, последующее наблюдение, правила добросовестного использования и порядок доступа.", keywords: "Teta2 цена, стоматологический ИИ цена, OPG AI подписка, программа для стоматологии" },
  },
  "/clinical-safety": {
    en: { title: "Teta2 Clinical Safety | Human-in-the-loop Dental AI", description: "Learn how Teta2 keeps dentists in control of AI-assisted OPG findings, clinical review, patient communication and follow-up decisions.", keywords: "Teta2 safety, dental AI safety, human in the loop, OPG AI clinical safety, dentist oversight" },
    hy: { title: "Teta2 կլինիկական անվտանգություն | AI՝ բժշկի վերահսկմամբ", description: "Իմացեք, թե ինչպես է Teta2-ը բժշկին պահում AI-աջակցվող OPG արդյունքների, կլինիկական վերանայման, պացիենտի հաղորդակցության և հետագա որոշումների վերահսկողության կենտրոնում։", keywords: "Teta2 անվտանգություն, ատամնաբուժական AI, OPG AI, բժշկի վերահսկում" },
    ru: { title: "Клиническая безопасность Teta2 | ИИ под контролем врача", description: "Узнайте, как Teta2 сохраняет контроль стоматолога над результатами OPG с поддержкой ИИ, клинической проверкой, сообщениями пациентам и последующим наблюдением.", keywords: "Teta2 безопасность, стоматологический ИИ, OPG AI, контроль врача, human in the loop" },
  },
  "/about": {
    en: { title: "About Teta2 | Team & Dental AI Project in Yerevan", description: "Meet Teta2 founder Typhon Namira and co-founder Van Arzoyan, and learn about the dental AI project's mission, product focus and contact details in Yerevan, Armenia.", keywords: "Teta2, Typhon Namira, Van Arzoyan, Teta2 founder, dental AI Yerevan, Armenia startup" },
    hy: { title: "Teta2-ի մասին | Թիմ և dental AI նախագիծ Երևանում", description: "Ծանոթացեք Teta2-ի հիմնադիր Typhon Namira-ին և համահիմնադիր Van Arzoyan-ին, նախագծի նպատակին, արտադրանքի ուղղությանը և Երևանի կապի տվյալներին։", keywords: "Teta2, Typhon Namira, Van Arzoyan, ատամնաբուժական AI Հայաստան, Երևան ստարտափ" },
    ru: { title: "О Teta2 | Команда и dental AI проект в Ереване", description: "Познакомьтесь с основателем Teta2 Typhon Namira и сооснователем Van Arzoyan, миссией проекта, продуктом и контактами в Ереване, Армения.", keywords: "Teta2, Typhon Namira, Van Arzoyan, стоматологический ИИ Армения, стартап Ереван" },
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

function setLink(rel: string, href: string) {
  const selector = `link[rel="${rel}"]:not([hreflang])`;
  let node = document.head.querySelector<HTMLLinkElement>(selector);
  if (!node) {
    node = document.createElement("link");
    node.rel = rel;
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
      const indexable = INDEXABLE_PATHS.has(path);
      const entry = SEO[path]?.[lang] ?? SEO["/"][lang];
      const canonicalPath = indexable ? path : "/";
      const canonical = `${BASE}${canonicalPath === "/" ? "/" : canonicalPath}`;

      document.title = indexable ? entry.title : `Teta2 | ${path === "/login" ? "Clinic Sign In" : "Clinical Platform"}`;
      document.documentElement.lang = lang;
      setMeta("description", indexable ? entry.description : "Secure Teta2 clinical platform access for authorized dental-clinic users.");
      setMeta("keywords", indexable ? entry.keywords : "Teta2");
      setMeta("robots", indexable ? "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1" : "noindex,nofollow,noarchive");
      setMeta("author", "Teta2");
      setMeta("og:type", "website", true);
      setMeta("og:site_name", "Teta2", true);
      setMeta("og:title", indexable ? entry.title : "Teta2 Clinical Platform", true);
      setMeta("og:description", indexable ? entry.description : "Secure Teta2 clinical platform access.", true);
      setMeta("og:url", canonical, true);
      setMeta("og:image", LOGO, true);
      setMeta("twitter:card", "summary");
      setMeta("twitter:title", indexable ? entry.title : "Teta2 Clinical Platform");
      setMeta("twitter:description", indexable ? entry.description : "Secure Teta2 clinical platform access.");
      setMeta("twitter:image", LOGO);
      setLink("canonical", canonical);

      if (indexable) applyStructuredData();
      else document.querySelectorAll('script[data-teta2-seo="true"]').forEach(node => node.remove());
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
