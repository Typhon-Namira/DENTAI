import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  Activity,
  CalendarCheck,
  CheckCircle2,
  CircleAlert,
  ExternalLink,
  MessageCircle,
  Radar,
  ShieldCheck,
} from "lucide-react";

import "./homepage-evidence-sections.css";

type Lang = "en" | "hy" | "ru";

type Copy = {
  evidenceEyebrow: string;
  evidenceTitle: string;
  evidenceLead: string;
  globalLabel: string;
  globalDetail: string;
  untreatedValue: string;
  untreatedLabel: string;
  untreatedDetail: string;
  commonValue: string;
  commonLabel: string;
  commonDetail: string;
  contextNote: string;
  source: string;
  consequenceEyebrow: string;
  consequenceTitle: string;
  consequenceLead: string;
  consequenceCards: Array<{ number: string; title: string; body: string; source: string }>;
  truthEyebrow: string;
  truthTitle: string;
  truthLead: string;
  truthCenter: string;
  truthItems: Array<{ title: string; body: string }>;
  truthFoot: string;
};

const COPY: Record<Lang, Copy> = {
  en: {
    evidenceEyebrow: "PUBLIC-HEALTH CONTEXT",
    evidenceTitle: "The problem is larger than the pain signal.",
    evidenceLead: "Teta2 does not turn population statistics into diagnostic claims. These numbers explain why structured dental follow-up matters even before a patient feels urgency.",
    globalLabel: "people are estimated to live with oral diseases worldwide",
    globalDetail: "World Health Organization · updated March 2025",
    untreatedValue: "1 in 5",
    untreatedLabel: "U.S. adults aged 20–64 had at least one untreated cavity",
    untreatedDetail: "CDC Oral Health Surveillance Report · 2017–March 2020 data, published 2024",
    commonValue: "#1",
    commonLabel: "Untreated caries in permanent teeth is the most common health condition in GBD 2021",
    commonDetail: "World Health Organization",
    contextNote: "Population-level context only. It does not mean every oral condition is visible on a panoramic radiograph, and it is not a performance claim for Teta2.",
    source: "Source",
    consequenceEyebrow: "WHY FOLLOW-UP MATTERS",
    consequenceTitle: "Untreated does not mean harmless.",
    consequenceLead: "The risk is not that every finding becomes severe. The risk is allowing a known or suspected problem to disappear from the clinic's attention after the image is reviewed.",
    consequenceCards: [
      { number: "01", title: "Decay can progress", body: "WHO notes that ongoing dental caries can lead to pain, tooth loss and infection.", source: "WHO" },
      { number: "02", title: "Infection can become urgent", body: "CDC notes that untreated cavities can lead to abscess; severe infection can spread beyond the tooth.", source: "CDC" },
      { number: "03", title: "Severe gum disease can cost teeth", body: "WHO reports that advanced periodontal disease can loosen teeth and may ultimately lead to tooth loss.", source: "WHO" },
    ],
    truthEyebrow: "NO MADE-UP OUTCOMES",
    truthTitle: "What Teta2 can show is more useful than a fake success rate.",
    truthLead: "Instead of claiming unmeasured outcomes, the workspace keeps concrete clinical and follow-up states visible to the clinic.",
    truthCenter: "VISIBLE STATE",
    truthItems: [
      { title: "Clinician-confirmed findings", body: "Possible findings stay tied to the OPG and the clinician's review state." },
      { title: "Patient-specific follow-up", body: "Follow-up is connected to the patient record rather than a generic reminder list." },
      { title: "Conversation status", body: "The team can see outreach and patient-message state instead of treating a sent message as a completed outcome." },
      { title: "Appointment status", body: "Proposed, approved, cancelled and completed states remain explicit in the workflow." },
    ],
    truthFoot: "Teta2 is designed to make the hand-off from radiograph to follow-up observable — not to replace the dentist's diagnosis or invent clinical results.",
  },
  hy: {
    evidenceEyebrow: "ՀԱՆՐԱՅԻՆ ԱՌՈՂՋՈՒԹՅԱՆ ՀԱՄԱՏԵՔՍՏ",
    evidenceTitle: "Խնդիրը ավելի մեծ է, քան ցավի ազդանշանը։",
    evidenceLead: "Teta2-ը բնակչության վիճակագրությունը չի վերածում ախտորոշման պնդումների։ Այս թվերը ցույց են տալիս, թե ինչու է կառուցվածքային dental follow-up-ը կարևոր՝ նույնիսկ մինչև պացիենտը հրատապություն զգա։",
    globalLabel: "մարդ ամբողջ աշխարհում, ըստ գնահատման, ունի բերանի խոռոչի հիվանդություն",
    globalDetail: "Առողջապահության համաշխարհային կազմակերպություն · թարմացված՝ մարտ 2025",
    untreatedValue: "1-ը 5-ից",
    untreatedLabel: "20–64 տարեկան ԱՄՆ մեծահասակներից ունեցել է առնվազն մեկ չբուժված կարիես",
    untreatedDetail: "CDC Oral Health Surveillance Report · 2017–2020 տվյալներ, հրապարակված 2024-ին",
    commonValue: "#1",
    commonLabel: "Մշտական ատամների չբուժված կարիեսը GBD 2021-ի ամենատարածված առողջական վիճակն է",
    commonDetail: "Առողջապահության համաշխարհային կազմակերպություն",
    contextNote: "Սա բնակչության մակարդակի համատեքստ է։ Այն չի նշանակում, որ բոլոր բերանի հիվանդությունները տեսանելի են պանորամիկ ռենտգենում, և Teta2-ի արդյունավետության պնդում չէ։",
    source: "Աղբյուր",
    consequenceEyebrow: "ԻՆՉՈՒ Է FOLLOW-UP-Ը ԿԱՐԵՎՈՐ",
    consequenceTitle: "Չբուժվածը չի նշանակում անվնաս։",
    consequenceLead: "Ռիսկը այն չէ, որ յուրաքանչյուր finding անպայման կդառնա ծանր։ Ռիսկն այն է, որ արդեն հայտնի կամ կասկածելի խնդիրը նկարի դիտումից հետո դուրս մնա կլինիկայի ուշադրությունից։",
    consequenceCards: [
      { number: "01", title: "Կարիեսը կարող է զարգանալ", body: "WHO-ն նշում է, որ շարունակվող կարիեսը կարող է բերել ցավի, ատամի կորստի և վարակի։", source: "WHO" },
      { number: "02", title: "Վարակը կարող է հրատապ դառնալ", body: "CDC-ն նշում է, որ չբուժված կարիեսը կարող է բերել աբսցեսի, իսկ ծանր վարակը՝ տարածվել ատամից դուրս։", source: "CDC" },
      { number: "03", title: "Ծանր լնդային հիվանդությունը կարող է բերել ատամի կորստի", body: "WHO-ի համաձայն՝ ծանր պերիօդոնտալ հիվանդությունը կարող է թուլացնել ատամները և վերջնականապես հանգեցնել դրանց կորստի։", source: "WHO" },
    ],
    truthEyebrow: "ԱՌԱՆՑ ՀՈՐԻՆՎԱԾ ԱՐԴՅՈՒՆՔՆԵՐԻ",
    truthTitle: "Teta2-ի տեսանելի փաստերը ավելի օգտակար են, քան հորինված success rate-ը։",
    truthLead: "Չչափված արդյունքներ խոստանալու փոխարեն՝ workspace-ը կլինիկային ցույց է տալիս իրական clinical և follow-up վիճակները։",
    truthCenter: "ՏԵՍԱՆԵԼԻ ՎԻՃԱԿ",
    truthItems: [
      { title: "Բժշկի հաստատած findings", body: "Հնարավոր findings-ը կապված են մնում OPG-ի և բժշկի review վիճակի հետ։" },
      { title: "Պացիենտին հատուկ follow-up", body: "Follow-up-ը կապված է պացիենտի քարտին, ոչ թե ընդհանուր reminder ցուցակին։" },
      { title: "Զրույցի վիճակ", body: "Թիմը տեսնում է outreach/message վիճակը՝ առանց ուղարկված հաղորդագրությունը վերջնական արդյունք համարելու։" },
      { title: "Այցի վիճակ", body: "Առաջարկված, հաստատված, չեղարկված և ավարտված վիճակները workflow-ում հստակ են։" },
    ],
    truthFoot: "Teta2-ը նախատեսված է ռենտգենից follow-up փոխանցումը տեսանելի դարձնելու համար, ոչ թե ատամնաբույժի ախտորոշումը փոխարինելու կամ clinical արդյունքներ հորինելու։",
  },
  ru: {
    evidenceEyebrow: "КОНТЕКСТ ОБЩЕСТВЕННОГО ЗДОРОВЬЯ",
    evidenceTitle: "Проблема больше, чем сигнал боли.",
    evidenceLead: "Teta2 не превращает статистику населения в диагностические заявления. Эти данные показывают, почему структурированное наблюдение важно еще до того, как пациент ощущает срочность.",
    globalLabel: "человек, по оценке, живут с заболеваниями полости рта во всем мире",
    globalDetail: "Всемирная организация здравоохранения · обновлено в марте 2025",
    untreatedValue: "1 из 5",
    untreatedLabel: "взрослых в США 20–64 лет имел как минимум одну нелеченную кариозную полость",
    untreatedDetail: "CDC Oral Health Surveillance Report · данные 2017–март 2020, опубликовано в 2024",
    commonValue: "#1",
    commonLabel: "Нелеченный кариес постоянных зубов — самое распространенное состояние здоровья по GBD 2021",
    commonDetail: "Всемирная организация здравоохранения",
    contextNote: "Это контекст на уровне населения. Он не означает, что все заболевания полости рта видны на панорамном снимке, и не является заявлением об эффективности Teta2.",
    source: "Источник",
    consequenceEyebrow: "ПОЧЕМУ FOLLOW-UP ВАЖЕН",
    consequenceTitle: "Нелеченное не означает безвредное.",
    consequenceLead: "Риск не в том, что каждая находка обязательно станет тяжелой. Риск — потерять известную или подозреваемую проблему из поля зрения клиники после просмотра снимка.",
    consequenceCards: [
      { number: "01", title: "Кариес может прогрессировать", body: "ВОЗ отмечает, что продолжающийся кариес может привести к боли, потере зуба и инфекции.", source: "WHO" },
      { number: "02", title: "Инфекция может стать неотложной", body: "CDC указывает, что нелеченный кариес может привести к абсцессу, а тяжелая инфекция — распространиться за пределы зуба.", source: "CDC" },
      { number: "03", title: "Тяжелая болезнь десен может привести к потере зубов", body: "По данным ВОЗ, тяжелый пародонтит может расшатывать зубы и в итоге приводить к их потере.", source: "WHO" },
    ],
    truthEyebrow: "БЕЗ ВЫДУМАННЫХ РЕЗУЛЬТАТОВ",
    truthTitle: "То, что Teta2 может показать, полезнее выдуманного success rate.",
    truthLead: "Вместо обещаний неизмеренных результатов workspace оставляет для клиники видимыми конкретные клинические и follow-up состояния.",
    truthCenter: "ВИДИМОЕ СОСТОЯНИЕ",
    truthItems: [
      { title: "Находки, подтвержденные врачом", body: "Возможные находки остаются связанными с OPG и состоянием клинического review." },
      { title: "Follow-up конкретного пациента", body: "Наблюдение связано с картой пациента, а не с общим списком напоминаний." },
      { title: "Статус общения", body: "Команда видит состояние outreach и сообщений, не выдавая отправленное сообщение за завершенный результат." },
      { title: "Статус визита", body: "Предложенные, подтвержденные, отмененные и завершенные визиты явно отражаются в workflow." },
    ],
    truthFoot: "Teta2 делает передачу от рентгенограммы к follow-up наблюдаемой — не заменяя диагноз стоматолога и не придумывая клинические результаты.",
  },
};

const WHO_URL = "https://www.who.int/news-room/fact-sheets/detail/oral-health";
const CDC_REPORT_URL = "https://www.cdc.gov/oral-health/php/2024-oral-health-surveillance-report/selected-findings.html";
const CDC_CAVITY_URL = "https://www.cdc.gov/oral-health/data-research/facts-stats/fast-facts-cavities.html";

function currentLanguage(): Lang {
  const value = localStorage.getItem("teta2-product-language") ?? localStorage.getItem("teta2-v4-language");
  return value === "hy" || value === "ru" ? value : "en";
}

function SourceLink({ href, children }: { href: string; children: React.ReactNode }) {
  return <a href={href} target="_blank" rel="noreferrer">{children}<ExternalLink size={12} /></a>;
}

function EvidenceContent({ lang }: { lang: Lang }) {
  const c = COPY[lang];
  return <div className="home-intel-root">
    <section className="home-intel-section home-intel-evidence" aria-labelledby="home-evidence-title">
      <div className="home-intel-heading">
        <span className="home-intel-eyebrow"><Radar size={15} />{c.evidenceEyebrow}</span>
        <h2 id="home-evidence-title">{c.evidenceTitle}</h2>
        <p>{c.evidenceLead}</p>
      </div>

      <div className="home-intel-evidence-grid">
        <article className="home-intel-orbit-card">
          <div className="home-intel-orbit" aria-hidden="true"><i/><i/><i/><span/></div>
          <div className="home-intel-orbit-copy">
            <strong>3.7B</strong>
            <p>{c.globalLabel}</p>
            <small>{c.globalDetail}</small>
          </div>
          <SourceLink href={WHO_URL}>{c.source}: WHO</SourceLink>
        </article>

        <div className="home-intel-stat-stack">
          <article className="home-intel-stat-card home-intel-stat-card--teal">
            <div><strong>{c.untreatedValue}</strong><CircleAlert size={20}/></div>
            <p>{c.untreatedLabel}</p>
            <small>{c.untreatedDetail}</small>
            <SourceLink href={CDC_REPORT_URL}>{c.source}: CDC</SourceLink>
          </article>
          <article className="home-intel-stat-card home-intel-stat-card--blue">
            <div><strong>{c.commonValue}</strong><Activity size={20}/></div>
            <p>{c.commonLabel}</p>
            <small>{c.commonDetail}</small>
            <SourceLink href={WHO_URL}>{c.source}: WHO</SourceLink>
          </article>
        </div>
      </div>

      <div className="home-intel-context-note"><ShieldCheck size={16}/><span>{c.contextNote}</span></div>
    </section>

    <section className="home-intel-section home-intel-consequence" aria-labelledby="home-consequence-title">
      <div className="home-intel-heading home-intel-heading--compact">
        <span className="home-intel-eyebrow"><CircleAlert size={15}/>{c.consequenceEyebrow}</span>
        <h2 id="home-consequence-title">{c.consequenceTitle}</h2>
        <p>{c.consequenceLead}</p>
      </div>
      <div className="home-intel-consequence-grid">
        {c.consequenceCards.map((item, index) => <article key={item.number} className="home-intel-consequence-card">
          <div className="home-intel-consequence-number">{item.number}</div>
          <div className="home-intel-consequence-line" aria-hidden="true"><span style={{ "--fill": `${72 + index * 10}%` } as React.CSSProperties}/></div>
          <h3>{item.title}</h3>
          <p>{item.body}</p>
          <SourceLink href={item.source === "CDC" ? CDC_CAVITY_URL : WHO_URL}>{c.source}: {item.source}</SourceLink>
        </article>)}
      </div>
    </section>

    <section className="home-intel-section home-intel-truth" aria-labelledby="home-truth-title">
      <div className="home-intel-truth-copy">
        <span className="home-intel-eyebrow"><CheckCircle2 size={15}/>{c.truthEyebrow}</span>
        <h2 id="home-truth-title">{c.truthTitle}</h2>
        <p>{c.truthLead}</p>
        <div className="home-intel-truth-foot"><ShieldCheck size={17}/><span>{c.truthFoot}</span></div>
      </div>
      <div className="home-intel-state-map" aria-label={c.truthCenter}>
        <div className="home-intel-state-core"><span>{c.truthCenter}</span><b>Teta2</b></div>
        <article className="home-intel-state-item state-a"><CheckCircle2/><div><strong>{c.truthItems[0].title}</strong><p>{c.truthItems[0].body}</p></div></article>
        <article className="home-intel-state-item state-b"><Radar/><div><strong>{c.truthItems[1].title}</strong><p>{c.truthItems[1].body}</p></div></article>
        <article className="home-intel-state-item state-c"><MessageCircle/><div><strong>{c.truthItems[2].title}</strong><p>{c.truthItems[2].body}</p></div></article>
        <article className="home-intel-state-item state-d"><CalendarCheck/><div><strong>{c.truthItems[3].title}</strong><p>{c.truthItems[3].body}</p></div></article>
      </div>
    </section>
  </div>;
}

export function HomepageEvidenceSections() {
  const [lang, setLang] = useState<Lang>(() => currentLanguage());
  const [home, setHome] = useState(() => window.location.pathname === "/");
  const [host, setHost] = useState<HTMLElement | null>(null);

  useEffect(() => {
    const syncRoute = () => setHome(window.location.pathname === "/");
    const syncLanguage = (event: Event) => {
      const next = (event as CustomEvent<Lang>).detail;
      setLang(next === "hy" || next === "ru" ? next : "en");
    };
    window.addEventListener("popstate", syncRoute);
    window.addEventListener("teta2-language-change", syncLanguage);
    return () => {
      window.removeEventListener("popstate", syncRoute);
      window.removeEventListener("teta2-language-change", syncLanguage);
    };
  }, []);

  useEffect(() => {
    let observer: MutationObserver | null = null;
    let cancelled = false;

    const removeHost = () => {
      const existing = document.getElementById("teta2-home-evidence-root");
      existing?.remove();
      if (!cancelled) setHost(null);
    };

    if (!home) {
      removeHost();
      return () => { cancelled = true; };
    }

    const mount = () => {
      if (cancelled) return true;
      const hero = document.querySelector<HTMLElement>(".product-home-hero");
      if (!hero) return false;
      let node = document.getElementById("teta2-home-evidence-root") as HTMLElement | null;
      if (!node) {
        node = document.createElement("div");
        node.id = "teta2-home-evidence-root";
        hero.insertAdjacentElement("afterend", node);
      }
      setHost(node);
      return true;
    };

    if (!mount()) {
      observer = new MutationObserver(() => { if (mount()) observer?.disconnect(); });
      observer.observe(document.getElementById("root") ?? document.body, { childList: true, subtree: true });
    }

    return () => {
      cancelled = true;
      observer?.disconnect();
      document.getElementById("teta2-home-evidence-root")?.remove();
    };
  }, [home]);

  return home && host ? createPortal(<EvidenceContent lang={lang}/>, host) : null;
}
