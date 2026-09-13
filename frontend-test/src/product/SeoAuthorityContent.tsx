import { useEffect } from "react";

type Language = "en" | "hy" | "ru";

type ProductCopy = {
  kicker: string;
  title: string;
  intro: string;
  cards: Array<{ title: string; body: string }>;
  principleTitle: string;
  principleBody: string;
  faqTitle: string;
  faq: Array<{ question: string; answer: string }>;
  links: { workflow: string; safety: string; pricing: string };
};

type FounderCopy = {
  kicker: string;
  title: string;
  lead: string;
  principleTitle: string;
  principleBody: string;
  aliases: string;
  imageAlt: string;
  productLink: string;
  metaTitle: string;
  metaDescription: string;
  metaKeywords: string;
  schemaName: string;
  schemaJobTitle: string;
  schemaDescription: string;
};

const BASE = "https://www.teta2.com";
const FOUNDER_IMAGE = "/images/typhon.jpg";

const PRODUCT_COPY: Record<Language, ProductCopy> = {
  en: {
    kicker: "Dental AI for clinical workflow",
    title: "Dental AI software for OPG and panoramic X-ray workflows",
    intro:
      "Teta2 is built for dental clinics that want to turn a panoramic dental X-ray (OPG) into a structured, clinician-reviewed workflow. AI-assisted analysis can organize possible findings, while the dentist reviews the result before it is used for patient records, follow-up or booking.",
    cards: [
      {
        title: "AI-assisted OPG review",
        body: "Use dental AI to review OPG and panoramic radiographs, organize possible findings by tooth and make the image easier to evaluate inside a clinical workflow.",
      },
      {
        title: "The dentist stays in control",
        body: "Teta2 is decision-support software, not a replacement for diagnosis. The clinician reviews the AI-assisted output and remains responsible for clinical interpretation and care decisions.",
      },
      {
        title: "From X-ray to patient follow-up",
        body: "Connect reviewed findings with the patient record, follow-up timing, multilingual outreach and appointment booking instead of leaving the panoramic image as an isolated file.",
      },
    ],
    principleTitle: "AI in dentistry should support the dentist, not replace clinical judgment",
    principleBody:
      "Teta2 combines dental X-ray AI with a clinician-controlled process. The goal is not to turn an AI suggestion into an automatic diagnosis; it is to help clinics structure OPG review, preserve the dentist's decision and turn relevant findings into timely patient follow-up.",
    faqTitle: "Dental AI and OPG analysis: common questions",
    faq: [
      {
        question: "What is dental AI software?",
        answer:
          "Dental AI software uses artificial intelligence to assist parts of a dental workflow. In Teta2, AI-assisted analysis helps organize possible findings from OPG and panoramic dental X-rays, while the dentist performs the clinical review.",
      },
      {
        question: "Can Teta2 analyze OPG and panoramic dental X-rays?",
        answer:
          "Teta2 supports AI-assisted review of OPG and panoramic dental X-ray images. The output is presented for clinician review rather than being treated as an automatic diagnosis.",
      },
      {
        question: "Does Teta2 replace the dentist?",
        answer:
          "No. Teta2 is designed to support a clinician-controlled workflow. The dentist remains responsible for interpreting the image, confirming findings and making clinical decisions.",
      },
      {
        question: "What happens after an OPG is reviewed?",
        answer:
          "Reviewed findings can be connected with the patient's record and used to organize tooth-specific follow-up, patient messaging and appointment booking.",
      },
    ],
    links: { workflow: "See how it works", safety: "Clinical AI safety", pricing: "View pricing" },
  },
  hy: {
    kicker: "Ատամնաբուժական AI՝ կլինիկական աշխատանքի համար",
    title: "Ատամնաբուժական AI՝ OPG և պանորամիկ ռենտգենային պատկերների համար",
    intro:
      "Teta2-ը նախատեսված է ատամնաբուժական կլինիկաների համար, որոնք ցանկանում են պանորամիկ ռենտգենը (OPG) վերածել կառուցվածքային և բժշկի կողմից վերահսկվող գործընթացի։ AI-աջակցվող վերլուծությունը կարող է համակարգել հնարավոր հայտնաբերումները, իսկ ատամնաբույժը վերանայում է արդյունքը՝ նախքան այն պացիենտի քարտում, հետագա վերահսկման կամ ամրագրման համար օգտագործելը։",
    cards: [
      {
        title: "OPG-ի AI-աջակցվող վերլուծություն",
        body: "Արհեստական բանականությունը օգնում է վերանայել OPG և պանորամիկ ռենտգենային պատկերները, հնարավոր հայտնաբերումները դասավորել ըստ ատամի և պատկերը ներառել հստակ կլինիկական գործընթացի մեջ։",
      },
      {
        title: "Վերջնական վերահսկողությունը բժշկինն է",
        body: "Teta2-ը որոշումների աջակցման գործիք է, ոչ թե ինքնուրույն ախտորոշում կատարող համակարգ։ Ատամնաբույժը վերանայում է AI-ի առաջարկները և ինքն է պատասխանատու կլինիկական մեկնաբանության ու բուժման որոշումների համար։",
      },
      {
        title: "Ռենտգենից մինչև պացիենտի հետագա վերահսկում",
        body: "Վերանայված տվյալները կարելի է կապել պացիենտի քարտի, հետագա վերահսկման ժամանակացույցի, բազմալեզու հաղորդագրությունների և այցի ամրագրման հետ։",
      },
    ],
    principleTitle: "Արհեստական բանականությունը ատամնաբուժությունում պետք է օգնի բժշկին, ոչ թե փոխարինի նրան",
    principleBody:
      "Teta2-ը համադրում է պանորամիկ ռենտգենի AI-աջակցվող վերլուծությունը բժշկի վերահսկմամբ աշխատանքային գործընթացի հետ։ Նպատակը AI-ի առաջարկը ավտոմատ ախտորոշում դարձնելը չէ, այլ OPG-ի վերանայումը համակարգելը, բժշկի որոշումը պահպանելը և կարևոր տվյալները ժամանակին պացիենտի հետագա վերահսկման վերածելը։",
    faqTitle: "Ատամնաբուժական AI և OPG վերլուծություն․ հաճախ տրվող հարցեր",
    faq: [
      {
        question: "Ի՞նչ է ատամնաբուժական AI ծրագիրը։",
        answer:
          "Ատամնաբուժական AI ծրագիրը արհեստական բանականության միջոցով աջակցում է կլինիկական աշխատանքի որոշ փուլերին։ Teta2-ում AI-ը օգնում է համակարգել OPG և պանորամիկ ռենտգենային պատկերների հնարավոր հայտնաբերումները, իսկ կլինիկական վերանայումը կատարում է ատամնաբույժը։",
      },
      {
        question: "Teta2-ը կարո՞ղ է վերլուծել OPG և պանորամիկ ռենտգենը։",
        answer:
          "Teta2-ը աջակցում է OPG և պանորամիկ ռենտգենային պատկերների AI-աջակցվող վերանայմանը։ Արդյունքը ներկայացվում է բժշկին ստուգման համար և չի համարվում ավտոմատ ախտորոշում։",
      },
      {
        question: "Teta2-ը փոխարինո՞ւմ է ատամնաբույժին։",
        answer:
          "Ոչ։ Teta2-ը ստեղծված է բժշկի վերահսկմամբ աշխատելու համար։ Պատկերի մեկնաբանությունը, հայտնաբերումների հաստատումը և կլինիկական որոշումները մնում են ատամնաբույժի պատասխանատվության ներքո։",
      },
      {
        question: "Ի՞նչ է տեղի ունենում OPG-ի վերանայումից հետո։",
        answer:
          "Վերանայված տվյալները կարող են կապվել պացիենտի քարտի հետ և օգտագործվել ատամ առ ատամ հետագա վերահսկման, հաղորդագրությունների և այցի ամրագրման կազմակերպման համար։",
      },
    ],
    links: { workflow: "Տեսնել՝ ինչպես է աշխատում", safety: "Կլինիկական AI-ի անվտանգություն", pricing: "Դիտել գները" },
  },
  ru: {
    kicker: "ИИ для стоматологического процесса",
    title: "ИИ для стоматологии: анализ ОПТГ и панорамных снимков",
    intro:
      "Teta2 создан для стоматологических клиник, которым нужен структурированный процесс работы с панорамным снимком зубов (ОПТГ). ИИ-анализ помогает систематизировать возможные находки, а стоматолог проверяет результат до того, как данные используются в карте пациента, последующем наблюдении или записи на прием.",
    cards: [
      {
        title: "ИИ-анализ ОПТГ",
        body: "Искусственный интеллект помогает просматривать ОПТГ и панорамные снимки зубов, группировать возможные находки по зубам и включать снимок в понятный клинический процесс.",
      },
      {
        title: "Контроль остается у стоматолога",
        body: "Teta2 — инструмент поддержки решений, а не система автоматической диагностики. Врач проверяет результат ИИ и остается ответственным за клиническую интерпретацию и решения по лечению.",
      },
      {
        title: "От снимка к наблюдению пациента",
        body: "Проверенные данные можно связать с картой пациента, сроками наблюдения, многоязычными сообщениями и записью на прием, чтобы ОПТГ не оставалась изолированным файлом.",
      },
    ],
    principleTitle: "Искусственный интеллект в стоматологии должен помогать врачу, а не заменять клиническое решение",
    principleBody:
      "Teta2 объединяет ИИ-анализ панорамных снимков с процессом, в котором решение остается за стоматологом. Цель — не превращать предложение ИИ в автоматический диагноз, а структурировать анализ ОПТГ, сохранить решение врача и организовать своевременное наблюдение пациента.",
    faqTitle: "ИИ в стоматологии и анализ ОПТГ: частые вопросы",
    faq: [
      {
        question: "Что такое ИИ для стоматологии?",
        answer:
          "ИИ для стоматологии использует искусственный интеллект для поддержки отдельных этапов работы клиники. В Teta2 ИИ помогает систематизировать возможные находки на ОПТГ и панорамных снимках, а клиническую проверку выполняет стоматолог.",
      },
      {
        question: "Может ли Teta2 анализировать ОПТГ и панорамные снимки зубов?",
        answer:
          "Teta2 поддерживает ИИ-анализ ОПТГ и панорамных снимков зубов. Результат предназначен для проверки врачом и не используется как автоматический диагноз.",
      },
      {
        question: "Заменяет ли Teta2 стоматолога?",
        answer:
          "Нет. Teta2 создан для процесса под контролем врача. Стоматолог отвечает за интерпретацию снимка, подтверждение находок и клинические решения.",
      },
      {
        question: "Что происходит после проверки ОПТГ?",
        answer:
          "Проверенные данные можно связать с картой пациента и использовать для наблюдения по конкретным зубам, сообщений пациенту и записи на прием.",
      },
    ],
    links: { workflow: "Как это работает", safety: "Безопасность клинического ИИ", pricing: "Посмотреть цены" },
  },
};

const FOUNDER_COPY: Record<Language, FounderCopy> = {
  en: {
    kicker: "Founder",
    title: "Typhon Namira — Founder of Teta2",
    lead:
      "Typhon Namira is the founder of Teta2, a dental AI software project based in Yerevan, Armenia. Teta2 focuses on AI-assisted OPG and panoramic dental X-ray review, clinician-controlled findings, patient records and follow-up workflows.",
    principleTitle: "Building clinician-controlled dental AI",
    principleBody:
      "Teta2 is built around a clear principle: artificial intelligence can assist with organizing possible findings and workflow, while the dentist remains responsible for clinical review and decisions.",
    aliases: "Name variants: Typhon Namira · Թայֆոն Նամիրա · Տայֆոն Նամիրա · Тайфон Намира · Тифон Намира",
    imageAlt: "Typhon Namira, founder of Teta2",
    productLink: "Explore Teta2 dental AI software",
    metaTitle: "Typhon Namira — Founder of Teta2 | Dental AI",
    metaDescription:
      "Typhon Namira is the founder of Teta2, a dental AI software project in Yerevan, Armenia focused on AI-assisted OPG review and clinician-controlled patient follow-up.",
    metaKeywords: "Typhon Namira, Teta2 founder, founder of Teta2, dental AI Armenia, dental AI Yerevan, Թայֆոն Նամիրա, Тайфон Намира",
    schemaName: "Typhon Namira",
    schemaJobTitle: "Founder of Teta2",
    schemaDescription: "Founder of Teta2, a dental AI software project based in Yerevan, Armenia.",
  },
  hy: {
    kicker: "Հիմնադիր",
    title: "Թայֆոն Նամիրա (Typhon Namira) — Teta2-ի հիմնադիր",
    lead:
      "Թայֆոն Նամիրան (Typhon Namira) Teta2-ի հիմնադիրն է։ Teta2-ը Երևանում ստեղծվող ատամնաբուժական AI նախագիծ է, որը կենտրոնացած է OPG և պանորամիկ ռենտգենային պատկերների AI-աջակցվող վերանայման, բժշկի վերահսկմամբ հայտնաբերումների, պացիենտի քարտի և հետագա վերահսկման վրա։",
    principleTitle: "Բժշկի վերահսկմամբ ատամնաբուժական AI",
    principleBody:
      "Teta2-ի հիմքում պարզ սկզբունք է․ արհեստական բանականությունը կարող է օգնել համակարգել հնարավոր հայտնաբերումներն ու աշխատանքային գործընթացը, իսկ կլինիկական վերանայումն ու որոշումները մնում են ատամնաբույժի պատասխանատվության ներքո։",
    aliases: "Անվան տարբերակներ՝ Թայֆոն Նամիրա · Տայֆոն Նամիրա · Typhon Namira · Тайфон Намира",
    imageAlt: "Թայֆոն Նամիրա՝ Teta2-ի հիմնադիր",
    productLink: "Ծանոթանալ Teta2 ատամնաբուժական AI ծրագրին",
    metaTitle: "Թայֆոն Նամիրա — Teta2-ի հիմնադիր | Ատամնաբուժական AI",
    metaDescription:
      "Թայֆոն Նամիրան (Typhon Namira) Teta2-ի հիմնադիրն է։ Teta2-ը Երևանում ստեղծվող ատամնաբուժական AI նախագիծ է՝ OPG-ի վերլուծության և բժշկի վերահսկմամբ պացիենտների հետագա աշխատանքի համար։",
    metaKeywords: "Թայֆոն Նամիրա, Տայֆոն Նամիրա, Typhon Namira, Teta2 հիմնադիր, ատամնաբուժական AI Հայաստան, ատամնաբուժական AI Երևան",
    schemaName: "Թայֆոն Նամիրա",
    schemaJobTitle: "Teta2-ի հիմնադիր",
    schemaDescription: "Teta2-ի հիմնադիր՝ Երևանում ստեղծվող ատամնաբուժական AI նախագծի։",
  },
  ru: {
    kicker: "Основатель",
    title: "Тайфон Намира (Typhon Namira) — основатель Teta2",
    lead:
      "Тайфон Намира (Typhon Namira) — основатель Teta2, проекта стоматологического ПО с ИИ из Еревана, Армения. Teta2 работает с ИИ-анализом ОПТГ и панорамных снимков, проверкой результатов стоматологом, картой пациента и последующим наблюдением.",
    principleTitle: "Стоматологический ИИ под контролем врача",
    principleBody:
      "В основе Teta2 простой принцип: искусственный интеллект может помогать систематизировать возможные находки и рабочий процесс, но клиническая проверка и решения остаются за стоматологом.",
    aliases: "Варианты имени: Тайфон Намира · Тифон Намира · Typhon Namira · Թայֆոն Նամիրա",
    imageAlt: "Тайфон Намира, основатель Teta2",
    productLink: "Подробнее о стоматологическом ИИ Teta2",
    metaTitle: "Тайфон Намира — основатель Teta2 | ИИ для стоматологии",
    metaDescription:
      "Тайфон Намира (Typhon Namira) — основатель Teta2, проекта стоматологического ИИ из Еревана для анализа ОПТГ и наблюдения пациентов под контролем врача.",
    metaKeywords: "Тайфон Намира, Тифон Намира, Typhon Namira, основатель Teta2, ИИ для стоматологии Армения, стоматологический ИИ Ереван",
    schemaName: "Тайфон Намира",
    schemaJobTitle: "Основатель Teta2",
    schemaDescription: "Основатель Teta2, проекта стоматологического ПО с ИИ из Еревана, Армения.",
  },
};

function routeInfo(): { path: string; language: Language } {
  const normalized = window.location.pathname.replace(/\/+$/, "") || "/";
  const localized = normalized.match(/^\/(hy|ru)(?:\/(.*))?$/);
  if (!localized) return { path: normalized, language: "en" };
  const language = localized[1] as Exclude<Language, "en">;
  const rest = localized[2]?.replace(/\/+$/, "") ?? "";
  return { path: rest ? `/${rest}` : "/", language };
}

function localizedPath(path: string, language: Language): string {
  if (language === "en") return path;
  return `/${language}${path}`;
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

function ensureStyle() {
  if (document.head.querySelector("style[data-teta2-seo-authority-style]")) return;
  const style = document.createElement("style");
  style.dataset.teta2SeoAuthorityStyle = "true";
  style.textContent = `
    .teta2-seo-authority { padding-top: clamp(32px, 5vw, 72px); padding-bottom: clamp(32px, 5vw, 72px); }
    .teta2-seo-authority .t2-seo-intro { max-width: 900px; line-height: 1.75; }
    .teta2-seo-authority .t2-seo-principle { max-width: 980px; margin: 36px auto 0; }
    .teta2-seo-authority .t2-seo-faq { display: grid; gap: 12px; max-width: 980px; margin: 28px auto 0; }
    .teta2-seo-authority .t2-seo-faq details { border: 1px solid rgba(15, 23, 42, .12); border-radius: 16px; padding: 16px 18px; background: rgba(255, 255, 255, .78); }
    .teta2-seo-authority .t2-seo-faq summary { cursor: pointer; font-weight: 700; }
    .teta2-seo-authority .t2-seo-faq p { margin: 10px 0 0; line-height: 1.7; }
    .teta2-seo-authority .t2-seo-links { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 28px; }
    .teta2-seo-authority .t2-seo-links a { text-decoration: none; }
    .t2-founder-card { display: grid; grid-template-columns: minmax(150px, 220px) minmax(0, 1fr); gap: clamp(22px, 4vw, 46px); align-items: center; max-width: 980px; margin: 28px auto 0; padding: clamp(20px, 3vw, 34px); border: 1px solid rgba(15, 23, 42, .12); border-radius: 24px; background: rgba(255, 255, 255, .82); }
    .t2-founder-card img { display: block; width: 100%; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 20px; }
    .t2-founder-card h3 { margin: 0 0 10px; }
    .t2-founder-card p { line-height: 1.72; }
    .t2-founder-aliases { font-size: .92rem; opacity: .76; }
    @media (max-width: 680px) {
      .t2-founder-card { grid-template-columns: 1fr; }
      .t2-founder-card img { width: min(220px, 70vw); margin: 0 auto; }
    }
  `;
  document.head.appendChild(style);
}

function createHeader(kicker: string, title: string, body?: string) {
  const header = document.createElement("header");
  header.className = "product-section-heading";
  const eyebrow = document.createElement("span");
  eyebrow.textContent = kicker;
  const heading = document.createElement("h2");
  heading.textContent = title;
  header.append(eyebrow, heading);
  if (body) {
    const paragraph = document.createElement("p");
    paragraph.textContent = body;
    paragraph.className = "t2-seo-intro";
    header.appendChild(paragraph);
  }
  return header;
}

function createProductAuthority(language: Language) {
  const copy = PRODUCT_COPY[language];
  const section = document.createElement("section");
  section.className = "product-section teta2-seo-authority";
  section.dataset.teta2SeoAuthority = "product";
  section.appendChild(createHeader(copy.kicker, copy.title, copy.intro));

  const cards = document.createElement("div");
  cards.className = "product-three-grid";
  copy.cards.forEach((item) => {
    const article = document.createElement("article");
    const heading = document.createElement("h3");
    heading.textContent = item.title;
    const body = document.createElement("p");
    body.textContent = item.body;
    article.append(heading, body);
    cards.appendChild(article);
  });
  section.appendChild(cards);

  const principle = document.createElement("div");
  principle.className = "product-principle t2-seo-principle";
  const principleTitle = document.createElement("h2");
  principleTitle.textContent = copy.principleTitle;
  const principleBody = document.createElement("p");
  principleBody.textContent = copy.principleBody;
  principle.append(principleTitle, principleBody);
  section.appendChild(principle);

  const faqHeading = document.createElement("h2");
  faqHeading.textContent = copy.faqTitle;
  faqHeading.style.marginTop = "42px";
  section.appendChild(faqHeading);
  const faq = document.createElement("div");
  faq.className = "t2-seo-faq";
  copy.faq.forEach((item) => {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = item.question;
    const answer = document.createElement("p");
    answer.textContent = item.answer;
    details.append(summary, answer);
    faq.appendChild(details);
  });
  section.appendChild(faq);

  const links = document.createElement("div");
  links.className = "t2-seo-links";
  const linkTargets: Array<[string, string]> = [
    ["/how-it-works", copy.links.workflow],
    ["/clinical-safety", copy.links.safety],
    ["/pricing", copy.links.pricing],
  ];
  linkTargets.forEach(([path, label], index) => {
    const link = document.createElement("a");
    link.href = localizedPath(path, language);
    link.textContent = label;
    link.className = index === 0 ? "product-primary" : "product-secondary";
    links.appendChild(link);
  });
  section.appendChild(links);
  return section;
}

function createFounderAuthority(language: Language) {
  const copy = FOUNDER_COPY[language];
  const section = document.createElement("section");
  section.className = "product-section teta2-seo-authority";
  section.dataset.teta2SeoAuthority = "founder";
  section.appendChild(createHeader(copy.kicker, copy.title, copy.lead));

  const card = document.createElement("article");
  card.className = "t2-founder-card";
  const image = document.createElement("img");
  image.src = FOUNDER_IMAGE;
  image.alt = copy.imageAlt;
  image.loading = "lazy";
  image.width = 640;
  image.height = 640;
  const body = document.createElement("div");
  const heading = document.createElement("h3");
  heading.textContent = copy.principleTitle;
  const paragraph = document.createElement("p");
  paragraph.textContent = copy.principleBody;
  const aliases = document.createElement("p");
  aliases.className = "t2-founder-aliases";
  aliases.textContent = copy.aliases;
  const productLink = document.createElement("a");
  productLink.href = localizedPath("/product", language);
  productLink.className = "product-secondary";
  productLink.textContent = copy.productLink;
  body.append(heading, paragraph, aliases, productLink);
  card.append(image, body);
  section.appendChild(card);
  return section;
}

function setAuthoritySchema(language: Language, path: string) {
  document.querySelectorAll('script[data-teta2-authority-schema="true"]').forEach((node) => node.remove());
  if (path !== "/product" && path !== "/about") return;

  const script = document.createElement("script");
  script.type = "application/ld+json";
  script.dataset.teta2AuthoritySchema = "true";

  if (path === "/product") {
    const copy = PRODUCT_COPY[language];
    script.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "@id": `${BASE}${localizedPath("/product", language)}#faq`,
      inLanguage: language,
      mainEntity: copy.faq.map((item) => ({
        "@type": "Question",
        name: item.question,
        acceptedAnswer: { "@type": "Answer", text: item.answer },
      })),
    });
  } else {
    const copy = FOUNDER_COPY[language];
    script.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@type": "Person",
      "@id": `${BASE}/about#typhon-namira`,
      name: copy.schemaName,
      alternateName: ["Typhon Namira", "Թայֆոն Նամիրա", "Տայֆոն Նամիրա", "Тайфон Намира", "Тифон Намира"],
      url: `${BASE}${localizedPath("/about", language)}#typhon-namira`,
      mainEntityOfPage: `${BASE}${localizedPath("/about", language)}`,
      image: `${BASE}${FOUNDER_IMAGE}`,
      jobTitle: copy.schemaJobTitle,
      description: copy.schemaDescription,
      worksFor: { "@id": `${BASE}/#organization`, "@type": "Organization", name: "Teta2" },
      sameAs: ["https://ru.linkedin.com/in/typhon-namira", "https://pulsemealx.com/aboutUs.html"],
    });
  }
  document.head.appendChild(script);
}

function applyFounderMeta(language: Language) {
  const copy = FOUNDER_COPY[language];
  document.title = copy.metaTitle;
  setMeta("description", copy.metaDescription);
  setMeta("keywords", copy.metaKeywords);
  setMeta("og:title", copy.metaTitle, true);
  setMeta("og:description", copy.metaDescription, true);
  setMeta("twitter:title", copy.metaTitle);
  setMeta("twitter:description", copy.metaDescription);
}

function applyAuthorityContent() {
  document.querySelectorAll("[data-teta2-seo-authority]").forEach((node) => node.remove());
  const { path, language } = routeInfo();
  setAuthoritySchema(language, path);

  if (path !== "/product" && path !== "/about") return;
  const main = document.querySelector<HTMLElement>(".product-marketing-page");
  if (!main) return;

  if (path === "/product") {
    main.appendChild(createProductAuthority(language));
    return;
  }

  applyFounderMeta(language);
  const founder = createFounderAuthority(language);
  const cta = main.querySelector(".product-final-cta");
  if (cta) main.insertBefore(founder, cta);
  else main.appendChild(founder);
}

export function SeoAuthorityContent() {
  useEffect(() => {
    ensureStyle();
    let timers: number[] = [];
    const schedule = () => {
      timers.forEach((timer) => window.clearTimeout(timer));
      timers = [
        window.setTimeout(applyAuthorityContent, 0),
        window.setTimeout(applyAuthorityContent, 80),
        window.setTimeout(applyAuthorityContent, 220),
      ];
    };

    schedule();
    window.addEventListener("popstate", schedule);
    window.addEventListener("teta2-language-change", schedule);
    window.addEventListener("teta2-localized-route", schedule);

    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
      window.removeEventListener("popstate", schedule);
      window.removeEventListener("teta2-language-change", schedule);
      window.removeEventListener("teta2-localized-route", schedule);
      document.querySelectorAll("[data-teta2-seo-authority]").forEach((node) => node.remove());
      document.querySelectorAll('script[data-teta2-authority-schema="true"]').forEach((node) => node.remove());
    };
  }, []);

  return null;
}
