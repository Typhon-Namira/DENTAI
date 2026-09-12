import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  CalendarDays,
  Check,
  CircleAlert,
  ClipboardCheck,
  ExternalLink,
  FileImage,
  FolderHeart,
  HeartPulse,
  LockKeyhole,
  Mail,
  MapPin,
  MessageCircle,
  Phone,
  Radar,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  UserRoundCheck,
  UsersRound,
} from "lucide-react";

import "./page-deck-sections.css";

type Lang = "en" | "hy" | "ru";
type DeckRoute = "/product" | "/how-it-works" | "/pricing" | "/clinical-safety" | "/about";

const WHO_AI = "https://www.who.int/publications/i/item/9789240029200";
const ADA_RADIOGRAPHS = "https://www.ada.org/resources/ada-library/oral-health-topics/x-rays-radiographs";
const TYPHON_LINKEDIN = "https://ru.linkedin.com/in/typhon-namira";
const PULSEMEAL_ABOUT = "https://pulsemealx.com/aboutUs.html";
const MAP_ADDRESS = "https://www.google.com/maps/search/?api=1&query=4%20Arshakunyats%20Avenue%2C%20Yerevan%2C%20Armenia";
const WHATSAPP = "https://wa.me/37493700251";

const TEXT = {
  en: {
    product: {
      kicker: "PRODUCT ARCHITECTURE",
      title: "One clinical loop. Four connected objects.",
      lead: "Teta2 is designed so the radiograph, the clinician's review, the patient record and the follow-up plan do not become four separate pieces of work.",
      layers: [
        ["OPG", "The panoramic image enters the patient's record and stays available in OPG history."],
        ["Possible findings", "AI-assisted outputs are organized for clinician examination rather than presented as a final diagnosis."],
        ["Clinical record", "Review decisions remain attached to the patient instead of living in an isolated AI result."],
        ["Follow-up", "Problem- or tooth-based follow-up can remain visible with message and return state."],
      ],
      anatomyKicker: "PATIENT-CENTERED DATA",
      anatomyTitle: "The image is important. The continuity around it is the product.",
      anatomyLead: "A Teta2 patient workspace is built around the pieces the clinic needs to reconnect later: identity and contact, OPG history, findings, review, follow-up and messages.",
      anatomy: ["Patient identity & contact", "OPG history", "AI-assisted findings", "Clinician review state", "Follow-up timing", "Message history"],
      boundaryKicker: "INTENTIONAL SCOPE",
      boundaryTitle: "Focused is a product decision.",
      does: ["OPG-centered workflow", "Clinician review of possible findings", "Patient-specific follow-up", "Message and follow-up state visibility"],
      doesnt: ["No autonomous diagnosis", "No claim of validated accuracy where validation is not published", "No attempt to replace the clinical examination", "Not positioned as a full billing or hospital ERP suite"],
      yes: "Teta2 is built to",
      no: "Teta2 is not built to",
    },
    how: {
      kicker: "AFTER THE AI OUTPUT",
      title: "The important part is what happens between states.",
      lead: "A useful clinical workflow does not stop when a model returns a result. Teta2 keeps the hand-offs explicit so the clinic can see what has — and has not — happened yet.",
      states: [
        ["UNREVIEWED", "Possible finding exists, but clinician review has not been completed."],
        ["REVIEWED", "The clinician has examined the finding in context."],
        ["SCHEDULED / DUE", "A follow-up exists with a visible timing state."],
        ["SENDING / SENT", "Patient outreach has a delivery state instead of disappearing after a click."],
        ["RETURN", "The clinic can reconnect the follow-up with the patient record when the patient comes back."],
      ],
      handoffKicker: "THREE HAND-OFFS",
      handoffTitle: "Automation moves information. Responsibility stays visible.",
      handoffs: [
        ["AI → Dentist", "The model proposes possible findings. The dentist examines them before they become clinical decisions."],
        ["Dentist → Record", "Review state is kept with the patient and OPG history, not as a detached result."],
        ["Record → Patient", "Follow-up messaging is connected to the patient's clinical context and visible timing."],
      ],
      stopKicker: "AUTOMATION BOUNDARIES",
      stopTitle: "What the system deliberately does not silently infer.",
      stop: ["A model output is not treated as a definitive diagnosis.", "A sent message is not treated as a completed clinical outcome.", "A due follow-up remains due until the workflow moves forward.", "The clinician remains responsible for diagnosis and care decisions."],
    },
    pricing: {
      kicker: "WHAT THE SUBSCRIPTION BUYS",
      title: "Pay for a working clinical loop, not for a dashboard full of decorative metrics.",
      lead: "The current Teta2 clinic subscription centers on OPG analysis, the patient record and the follow-up workflow shown across this site.",
      included: ["AI-assisted OPG analysis", "Possible findings for clinician review", "Smart patient record and OPG history", "Problem/tooth-based follow-up timing", "Patient messaging workflow", "Follow-up and patient-return visibility"],
      fairKicker: "NORMAL CLINICAL USE",
      fairTitle: "No per-OPG counter for normal clinic use.",
      fairBody: "The public pricing copy currently describes OPG analysis as unlimited during the subscription period for normal clinical use. Fair Use applies to abnormal automated bulk processing or API abuse.",
      annualKicker: "ANNUAL OPTION",
      annualTitle: "12 months of access for the price of 10 months.",
      annualBody: "The annual option shown by Teta2 is simple: ten paid monthly periods provide twelve months of access.",
      paid: "paid",
      includedWord: "included",
      accessKicker: "ACCESS & CONTINUITY",
      accessTitle: "Clinic access is provisioned deliberately.",
      accessItems: [
        ["Request", "A clinic submits an access request rather than receiving an anonymous instant workspace."],
        ["Review", "The clinic is reviewed before credentials and workspace access are provisioned."],
        ["Renew", "When a subscription is renewed, the intention is continuity of the same clinical workspace rather than starting a new record set."],
      ],
      accessNote: "Public self-service provisioning is not enabled yet. Pricing shown on the live page remains the source of truth for the currently displayed market and plan.",
    },
    safety: {
      kicker: "CLAIMS BOUNDARY",
      title: "Clinical language is part of the safety system.",
      lead: "Teta2 deliberately separates an AI-assisted possible finding from a dentist's diagnosis. The wording shown to clinics should preserve that difference.",
      say: "Language Teta2 can responsibly use",
      dont: "Claims Teta2 should not make without evidence",
      sayItems: ["Possible finding", "AI-assisted analysis", "Requires dentist examination", "Clinician reviewed / unreviewed"],
      dontItems: ["Definitive diagnosis from AI alone", "Guaranteed detection", "Guaranteed clinical outcome", "Accuracy percentages that have not been validated and published"],
      humanKicker: "HUMAN CONTROL",
      humanTitle: "AI can surface information. The clinician keeps the decision gate.",
      humanBody: "WHO guidance on AI for health emphasizes ethics, accountability and appropriate human oversight. Teta2's public product language follows that direction by keeping model output reviewable rather than autonomous.",
      humanFlow: [["01", "AI-assisted output"], ["02", "Dentist examination"], ["03", "Confirm / reject in context"], ["04", "Follow-up or care decision"]],
      imagingKicker: "IMAGING CONTEXT",
      imagingTitle: "An OPG is clinical evidence — not the entire clinical examination.",
      imagingBody: "The ADA and AAOMR's 2026 radiography recommendations emphasize clinical examination and patient-specific need when deciding how radiographic imaging supports diagnosis, treatment planning and clinical management.",
      source: "Read source",
      safetyFoot: "Teta2 is a clinical decision-support workflow. It does not remove the need for professional examination, appropriate imaging selection or dentist responsibility.",
    },
    about: {
      kicker: "ABOUT TETA2",
      title: "A focused dental AI project built in Yerevan.",
      lead: "Teta2 is being built around one narrow problem: helping clinics carry an OPG from review into a patient record and a visible follow-up workflow. It is presented on this site as a pre-incorporation software project, not as a claim of regulatory approval or clinical autonomy.",
      principle: "The product principle is simple: the radiograph should not become an isolated AI result. It should remain connected to the clinician, the patient and the next action.",
      teamKicker: "TEAM",
      teamTitle: "People currently identified with the project.",
      typhonRole: "Founder · Teta2",
      typhonBody: "Typhon Namira is the founder of Teta2. Public profiles also identify him as the founder of PulseMeal and as Founder & CEO of Namira Group.",
      vanRole: "Co-founder · Technical / AI model fine-tuning",
      vanBody: "Van Arzoyan has worked on the technical side of Teta2, including AI model fine-tuning.",
      publicProfile: "Public profile",
      publicSource: "Public source",
      contactKicker: "CONTACT",
      contactTitle: "Talk directly to the Teta2 team.",
      email: "Email",
      phone: "Phone",
      whatsapp: "WhatsApp",
      telegram: "Telegram",
      office: "Office",
      address: "4 Arshakunyats Avenue, Yerevan, Armenia",
      contactNote: "For clinic access, product questions, technical discussions or partnerships, use the contact channel that is most convenient for you.",
    },
  },
  hy: {
    product: {
      kicker: "ԱՐՏԱԴՐԱՆՔԻ ՃԱՐՏԱՐԱՊԵՏՈՒԹՅՈՒՆ",
      title: "Մեկ կլինիկական շղթա։ Չորս կապված օբյեկտ։",
      lead: "Teta2-ը նախագծված է այնպես, որ ռենտգենը, բժշկի review-ը, պացիենտի քարտը և follow-up-ը չդառնան չորս առանձին աշխատանք։",
      layers: [["OPG", "Պանորամիկ պատկերը մտնում է պացիենտի քարտ և մնում OPG պատմության մեջ։"], ["Հնարավոր findings", "AI-ի արդյունքները ներկայացվում են բժշկի քննության համար, ոչ որպես վերջնական ախտորոշում։"], ["Կլինիկական քարտ", "Review որոշումները մնում են պացիենտի հետ կապված։"], ["Follow-up", "Խնդրի կամ ատամի հիմքով follow-up-ը մնում է տեսանելի՝ հաղորդագրության և վերադարձի վիճակով։"]],
      anatomyKicker: "ՊԱՑԻԵՆՏԱԿԵՆՏՐՈՆ ՏՎՅԱԼՆԵՐ",
      anatomyTitle: "Պատկերը կարևոր է։ Արժեքը՝ դրա շուրջ շարունակականությունն է։",
      anatomyLead: "Teta2-ի patient workspace-ը պահում է այն մասերը, որոնց կլինիկան պետք է վերադառնա՝ կոնտակտ, OPG պատմություն, findings, review, follow-up և հաղորդագրություններ։",
      anatomy: ["Պացիենտի տվյալներ և կոնտակտ", "OPG պատմություն", "AI-assisted findings", "Բժշկի review վիճակ", "Follow-up ժամանակավորում", "Հաղորդագրությունների պատմություն"],
      boundaryKicker: "ԳԻՏԱԿՑՎԱԾ ՍԱՀՄԱՆՆԵՐ",
      boundaryTitle: "Նեղ ֆոկուսը product որոշում է։",
      does: ["OPG-կենտրոն workflow", "Բժշկի review", "Պացիենտին հատուկ follow-up", "Հաղորդագրության և follow-up վիճակների տեսանելիություն"],
      doesnt: ["Ոչ ինքնավար ախտորոշում", "Ոչ չհրապարակված accuracy claim", "Ոչ կլինիկական քննության փոխարինում", "Ոչ ամբողջական billing կամ hospital ERP"],
      yes: "Teta2-ը ստեղծված է",
      no: "Teta2-ը ստեղծված չէ",
    },
    how: {
      kicker: "AI ԱՐԴՅՈՒՆՔԻՑ ՀԵՏՈ",
      title: "Կարևորը վիճակների միջև տեղի ունեցողն է։",
      lead: "Օգտակար clinical workflow-ը չի ավարտվում մոդելի պատասխանից հետո։ Teta2-ը պահում է hand-off-ները տեսանելի, որպեսզի կլինիկան իմանա՝ ինչն է կատարվել և ինչը դեռ ոչ։",
      states: [["UNREVIEWED", "Finding-ը կա, բայց բժշկի review-ը դեռ ավարտված չէ։"], ["REVIEWED", "Բժիշկը ուսումնասիրել է finding-ը clinical context-ում։"], ["SCHEDULED / DUE", "Follow-up-ը ունի տեսանելի ժամանակային վիճակ։"], ["SENDING / SENT", "Պացիենտի հաղորդագրությունն ունի delivery state։"], ["RETURN", "Վերադարձի պահին follow-up-ը կրկին կապվում է պացիենտի քարտին։"]],
      handoffKicker: "ԵՐԵՔ HAND-OFF",
      handoffTitle: "Ավտոմատացումը տեղափոխում է ինֆորմացիան։ Պատասխանատվությունը մնում է տեսանելի։",
      handoffs: [["AI → Բժիշկ", "Մոդելը առաջարկում է possible findings, բժիշկը դրանք ուսումնասիրում է մինչև clinical որոշումը։"], ["Բժիշկ → Քարտ", "Review վիճակը պահվում է պացիենտի և OPG պատմության հետ։"], ["Քարտ → Պացիենտ", "Follow-up հաղորդագրությունը կապված է clinical context-ի և ժամանակավորման հետ։"]],
      stopKicker: "ԱՎՏՈՄԱՏԱՑՄԱՆ ՍԱՀՄԱՆ",
      stopTitle: "Ինչը համակարգը դիտավորյալ չի ենթադրում ինքնուրույն։",
      stop: ["Model output-ը վերջնական ախտորոշում չէ։", "Ուղարկված հաղորդագրությունը ավարտված clinical outcome չէ։", "Due follow-up-ը մնում է due մինչև workflow-ը առաջ շարժվի։", "Ախտորոշման և բուժման որոշումը բժշկինն է։"],
    },
    pricing: {
      kicker: "ԻՆՉԻ ՀԱՄԱՐ Է ԲԱԺԱՆՈՐԴԱԳՐՈՒԹՅՈՒՆԸ",
      title: "Վճարեք աշխատող clinical loop-ի համար, ոչ դեկորատիվ dashboard-ի։",
      lead: "Teta2-ի ներկայիս clinic subscription-ը կենտրոնացած է OPG analysis-ի, patient record-ի և follow-up workflow-ի վրա։",
      included: ["AI-assisted OPG analysis", "Possible findings բժշկի review-ի համար", "Smart patient record և OPG history", "Problem/tooth-based follow-up timing", "Patient messaging workflow", "Follow-up և patient-return visibility"],
      fairKicker: "ՍՈՎՈՐԱԿԱՆ ԿԼԻՆԻԿԱԿԱՆ ՕԳՏԱԳՈՐԾՈՒՄ",
      fairTitle: "Սովորական clinic use-ի համար per-OPG counter չկա։",
      fairBody: "Public pricing copy-ը OPG analysis-ը նկարագրում է որպես unlimited subscription-ի ընթացքում սովորական clinical use-ի համար։ Fair Use-ը կիրառվում է abnormal automated bulk processing կամ API abuse-ի դեպքում։",
      annualKicker: "ՏԱՐԵԿԱՆ ՏԱՐԲԵՐԱԿ",
      annualTitle: "12 ամիս access՝ 10 ամսվա գնով։",
      annualBody: "Տարեկան տարբերակում տասը վճարված ամսական շրջան տալիս է տասներկու ամիս access։",
      paid: "վճարված",
      includedWord: "ներառված",
      accessKicker: "ACCESS & CONTINUITY",
      accessTitle: "Clinic access-ը provision է արվում վերահսկված ձևով։",
      accessItems: [["Հարցում", "Կլինիկան ուղարկում է access request։"], ["Review", "Կլինիկան ստուգվում է մինչև credentials-ի և workspace-ի ակտիվացումը։"], ["Renew", "Renewal-ը նախատեսված է նույն clinical workspace-ի շարունակության համար։"]],
      accessNote: "Public self-service provisioning-ը դեռ միացված չէ։ Live pricing page-ի ցուցադրած գինն ու market-ը մնում են ընթացիկ source of truth։",
    },
    safety: {
      kicker: "CLAIMS BOUNDARY",
      title: "Կլինիկական լեզուն safety system-ի մի մասն է։",
      lead: "Teta2-ը հստակ տարբերակում է AI-assisted possible finding-ը բժշկի ախտորոշումից։",
      say: "Պատասխանատու ձևակերպումներ",
      dont: "Պնդումներ, որոնք առանց ապացույցի չպետք է արվեն",
      sayItems: ["Possible finding", "AI-assisted analysis", "Requires dentist examination", "Clinician reviewed / unreviewed"],
      dontItems: ["AI-only definitive diagnosis", "Guaranteed detection", "Guaranteed clinical outcome", "Չվավերացված accuracy տոկոսներ"],
      humanKicker: "ՄԱՐԴԿԱՅԻՆ ՎԵՐԱՀՍԿՈՂՈՒԹՅՈՒՆ",
      humanTitle: "AI-ը կարող է surface անել ինֆորմացիան։ Որոշման դարպասը բժշկինն է։",
      humanBody: "WHO-ի AI for health guidance-ը շեշտում է ethics, accountability և appropriate human oversight-ը։ Teta2-ի public language-ը model output-ը պահում է reviewable, ոչ autonomous։",
      humanFlow: [["01", "AI-assisted output"], ["02", "Բժշկի քննություն"], ["03", "Confirm / reject context-ում"], ["04", "Follow-up կամ care decision"]],
      imagingKicker: "IMAGING CONTEXT",
      imagingTitle: "OPG-ն clinical evidence է, ոչ ամբողջ clinical examination-ը։",
      imagingBody: "ADA և AAOMR 2026 recommendations-ը շեշտում են clinical examination-ը և patient-specific need-ը՝ radiographic imaging-ի ընտրության և օգտագործման ժամանակ։",
      source: "Կարդալ աղբյուրը",
      safetyFoot: "Teta2-ը clinical decision-support workflow է։ Այն չի վերացնում professional examination-ի, appropriate imaging selection-ի կամ dentist responsibility-ի անհրաժեշտությունը։",
    },
    about: {
      kicker: "TETA2-Ի ՄԱՍԻՆ",
      title: "Ֆոկուսավորված dental AI նախագիծ՝ կառուցվող Երևանում։",
      lead: "Teta2-ը կառուցվում է մեկ նեղ խնդրի շուրջ՝ օգնել կլինիկաներին OPG review-ը կապել patient record-ի և տեսանելի follow-up workflow-ի հետ։ Կայքում այն ներկայացված է որպես pre-incorporation software project, ոչ regulatory approval կամ clinical autonomy claim։",
      principle: "Սկզբունքը պարզ է՝ ռենտգենը չպետք է դառնա մեկուսացված AI արդյունք։ Այն պետք է կապված մնա բժշկի, պացիենտի և հաջորդ գործողության հետ։",
      teamKicker: "ԹԻՄ",
      teamTitle: "Նախագծի հետ ներկայում նույնականացված մարդիկ։",
      typhonRole: "Founder · Teta2",
      typhonBody: "Typhon Namira-ն Teta2-ի founder-ն է։ Public profiles-ը նաև ներկայացնում են նրան որպես PulseMeal-ի founder և Namira Group-ի Founder & CEO։",
      vanRole: "Co-founder · Technical / AI model fine-tuning",
      vanBody: "Van Arzoyan-ը աշխատել է Teta2-ի technical մասի վրա, ներառյալ AI model fine-tuning-ը։",
      publicProfile: "Public profile",
      publicSource: "Public source",
      contactKicker: "ԿԱՊ",
      contactTitle: "Կապվեք անմիջապես Teta2 թիմի հետ։",
      email: "Email", phone: "Հեռախոս", whatsapp: "WhatsApp", telegram: "Telegram", office: "Գրասենյակ",
      address: "4 Arshakunyats Avenue, Yerevan, Armenia",
      contactNote: "Clinic access-ի, product հարցերի, technical քննարկումների կամ partnership-ի համար օգտագործեք ձեզ հարմար կապի տարբերակը։",
    },
  },
  ru: {
    product: {
      kicker: "АРХИТЕКТУРА ПРОДУКТА",
      title: "Один клинический цикл. Четыре связанные сущности.",
      lead: "Teta2 устроен так, чтобы снимок, review врача, карта пациента и follow-up не превращались в четыре отдельные задачи.",
      layers: [["OPG", "Панорамный снимок входит в карту пациента и остается в истории OPG."], ["Возможные находки", "AI-assisted результаты организованы для оценки врачом, а не выдаются как финальный диагноз."], ["Клиническая запись", "Решения review остаются связанными с пациентом."], ["Follow-up", "Наблюдение по проблеме или зубу остается видимым вместе со статусом сообщений и возврата пациента."]],
      anatomyKicker: "ДАННЫЕ ВОКРУГ ПАЦИЕНТА",
      anatomyTitle: "Снимок важен. Продукт — это непрерывность вокруг него.",
      anatomyLead: "Patient workspace Teta2 связывает контакт, историю OPG, findings, review, follow-up и сообщения.",
      anatomy: ["Данные и контакт пациента", "История OPG", "AI-assisted findings", "Статус review врача", "Срок follow-up", "История сообщений"],
      boundaryKicker: "ОСОЗНАННЫЕ ГРАНИЦЫ",
      boundaryTitle: "Фокус — это продуктовое решение.",
      does: ["OPG-центричный workflow", "Review возможных findings врачом", "Follow-up конкретного пациента", "Видимость статусов сообщений и follow-up"],
      doesnt: ["Не автономный диагноз", "Не заявляет непроверенную accuracy", "Не заменяет клинический осмотр", "Не позиционируется как полный billing или hospital ERP"],
      yes: "Teta2 создан для",
      no: "Teta2 не создан для",
    },
    how: {
      kicker: "ПОСЛЕ ВЫВОДА AI",
      title: "Самое важное происходит между состояниями.",
      lead: "Полезный clinical workflow не заканчивается ответом модели. Teta2 делает hand-off видимым, чтобы клиника понимала, что уже произошло, а что еще нет.",
      states: [["UNREVIEWED", "Finding существует, но review врача еще не завершен."], ["REVIEWED", "Врач оценил finding в клиническом контексте."], ["SCHEDULED / DUE", "Follow-up имеет явный временной статус."], ["SENDING / SENT", "У outreach есть статус доставки."], ["RETURN", "При возврате пациента follow-up снова связан с его картой."]],
      handoffKicker: "ТРИ HAND-OFF",
      handoffTitle: "Автоматизация переносит информацию. Ответственность остается видимой.",
      handoffs: [["AI → Врач", "Модель предлагает possible findings, врач оценивает их до клинического решения."], ["Врач → Карта", "Review хранится вместе с пациентом и историей OPG."], ["Карта → Пациент", "Follow-up сообщения связаны с clinical context и сроками."]],
      stopKicker: "ГРАНИЦЫ АВТОМАТИЗАЦИИ",
      stopTitle: "Что система намеренно не предполагает молча.",
      stop: ["Model output не является финальным диагнозом.", "Отправленное сообщение не равно завершенному clinical outcome.", "Due follow-up остается due, пока workflow не продвинулся.", "Диагноз и решения о лечении остаются ответственностью врача."],
    },
    pricing: {
      kicker: "ЧТО ОПЛАЧИВАЕТ ПОДПИСКА",
      title: "Платите за рабочий clinical loop, а не за декоративные метрики.",
      lead: "Текущая clinic subscription Teta2 сосредоточена на OPG analysis, patient record и follow-up workflow.",
      included: ["AI-assisted OPG analysis", "Possible findings для review врача", "Smart patient record и история OPG", "Problem/tooth-based follow-up timing", "Patient messaging workflow", "Видимость follow-up и возврата пациента"],
      fairKicker: "ОБЫЧНОЕ КЛИНИЧЕСКОЕ ИСПОЛЬЗОВАНИЕ",
      fairTitle: "Нет per-OPG счетчика для обычной работы клиники.",
      fairBody: "Публичная pricing copy описывает OPG analysis как unlimited в период подписки при обычном клиническом использовании. Fair Use применяется к аномальной автоматизированной массовой обработке или API abuse.",
      annualKicker: "ГОДОВОЙ ВАРИАНТ",
      annualTitle: "12 месяцев доступа по цене 10 месяцев.",
      annualBody: "Годовой вариант Teta2: десять оплаченных месячных периодов дают двенадцать месяцев доступа.",
      paid: "оплачено", includedWord: "включено",
      accessKicker: "ACCESS & CONTINUITY",
      accessTitle: "Доступ клиники provisioned намеренно.",
      accessItems: [["Запрос", "Клиника отправляет access request."], ["Review", "Клиника проходит review до выдачи credentials и workspace."], ["Renew", "Продление рассчитано на продолжение того же clinical workspace."]],
      accessNote: "Public self-service provisioning пока не включен. Цена и market на live pricing page остаются текущим source of truth.",
    },
    safety: {
      kicker: "ГРАНИЦА CLAIMS",
      title: "Клинический язык — часть safety system.",
      lead: "Teta2 сознательно отделяет AI-assisted possible finding от диагноза стоматолога.",
      say: "Формулировки, которые можно использовать ответственно",
      dont: "Claims, которые нельзя делать без доказательств",
      sayItems: ["Possible finding", "AI-assisted analysis", "Requires dentist examination", "Clinician reviewed / unreviewed"],
      dontItems: ["Definitive diagnosis только от AI", "Guaranteed detection", "Guaranteed clinical outcome", "Невалидированные проценты accuracy"],
      humanKicker: "КОНТРОЛЬ ЧЕЛОВЕКА",
      humanTitle: "AI может показать информацию. Решение остается за врачом.",
      humanBody: "WHO guidance по AI for health подчеркивает ethics, accountability и appropriate human oversight. Публичный язык Teta2 сохраняет model output reviewable, а не autonomous.",
      humanFlow: [["01", "AI-assisted output"], ["02", "Осмотр стоматолога"], ["03", "Confirm / reject в контексте"], ["04", "Follow-up или care decision"]],
      imagingKicker: "IMAGING CONTEXT",
      imagingTitle: "OPG — клиническое свидетельство, а не весь клинический осмотр.",
      imagingBody: "Рекомендации ADA и AAOMR 2026 подчеркивают clinical examination и индивидуальную необходимость при выборе и использовании radiographic imaging.",
      source: "Открыть источник",
      safetyFoot: "Teta2 — clinical decision-support workflow. Он не отменяет professional examination, appropriate imaging selection или ответственность стоматолога.",
    },
    about: {
      kicker: "О TETA2",
      title: "Фокусированный dental AI проект, создаваемый в Ереване.",
      lead: "Teta2 строится вокруг одной узкой задачи: связать OPG review с patient record и видимым follow-up workflow. На сайте проект представлен как pre-incorporation software project, а не как заявление о regulatory approval или clinical autonomy.",
      principle: "Принцип простой: рентгенограмма не должна становиться изолированным AI результатом. Она должна оставаться связанной с врачом, пациентом и следующим действием.",
      teamKicker: "КОМАНДА",
      teamTitle: "Люди, которые сейчас указаны в проекте.",
      typhonRole: "Founder · Teta2",
      typhonBody: "Typhon Namira — founder Teta2. Публичные профили также указывают его как founder PulseMeal и Founder & CEO Namira Group.",
      vanRole: "Co-founder · Technical / AI model fine-tuning",
      vanBody: "Van Arzoyan работал над технической частью Teta2, включая AI model fine-tuning.",
      publicProfile: "Public profile", publicSource: "Public source",
      contactKicker: "КОНТАКТ",
      contactTitle: "Свяжитесь напрямую с командой Teta2.",
      email: "Email", phone: "Телефон", whatsapp: "WhatsApp", telegram: "Telegram", office: "Офис",
      address: "4 Arshakunyats Avenue, Yerevan, Armenia",
      contactNote: "Для clinic access, product вопросов, технических обсуждений или партнерств используйте удобный канал связи.",
    },
  },
} as const;

function ProductDeck({ lang }: { lang: Lang }) {
  const c = TEXT[lang].product;
  return <div className="page-deck page-deck-product">
    <section className="deck-section deck-product-stack">
      <DeckHeading kicker={c.kicker} title={c.title} lead={c.lead}/>
      <div className="deck-layer-rail">
        {c.layers.map(([title, body], index) => <article key={title}>
          <span>0{index + 1}</span><div><strong>{title}</strong><p>{body}</p></div>{index < c.layers.length - 1 && <ArrowRight aria-hidden="true"/>}
        </article>)}
      </div>
    </section>
    <section className="deck-section deck-product-anatomy">
      <div className="deck-copy-column"><DeckHeading kicker={c.anatomyKicker} title={c.anatomyTitle} lead={c.anatomyLead}/></div>
      <div className="deck-record-sheet">
        <div className="deck-record-top"><span><UserRoundCheck/>PATIENT WORKSPACE</span><i/></div>
        {c.anatomy.map((item, index) => <div className="deck-record-row" key={item}><b>{String(index + 1).padStart(2,"0")}</b><span>{item}</span><Check size={16}/></div>)}
      </div>
    </section>
    <section className="deck-section deck-product-boundary">
      <DeckHeading kicker={c.boundaryKicker} title={c.boundaryTitle}/>
      <div className="deck-boundary-grid">
        <article><span className="deck-boundary-label good"><Check/>{c.yes}</span>{c.does.map(item=><p key={item}>{item}</p>)}</article>
        <article><span className="deck-boundary-label guard"><ShieldCheck/>{c.no}</span>{c.doesnt.map(item=><p key={item}>{item}</p>)}</article>
      </div>
    </section>
  </div>;
}

function HowDeck({ lang }: { lang: Lang }) {
  const c = TEXT[lang].how;
  return <div className="page-deck page-deck-how">
    <section className="deck-section deck-state-section">
      <DeckHeading kicker={c.kicker} title={c.title} lead={c.lead}/>
      <div className="deck-state-track">
        {c.states.map(([state, body], index) => <article key={state}><span className="deck-state-dot">{index + 1}</span><strong>{state}</strong><p>{body}</p></article>)}
      </div>
    </section>
    <section className="deck-section deck-handoff-section">
      <DeckHeading kicker={c.handoffKicker} title={c.handoffTitle}/>
      <div className="deck-handoff-grid">
        {c.handoffs.map(([title, body], index) => <article key={title}><div className="deck-handoff-icon">{index===0?<BrainCircuit/>:index===1?<FolderHeart/>:<MessageCircle/>}</div><b>{title}</b><p>{body}</p></article>)}
      </div>
    </section>
    <section className="deck-section deck-stop-section">
      <div><DeckHeading kicker={c.stopKicker} title={c.stopTitle}/></div>
      <div className="deck-stop-list">{c.stop.map((item,index)=><p key={item}><span>0{index+1}</span>{item}</p>)}</div>
    </section>
  </div>;
}

function PricingDeck({ lang }: { lang: Lang }) {
  const c = TEXT[lang].pricing;
  return <div className="page-deck page-deck-pricing">
    <section className="deck-section deck-pricing-value">
      <DeckHeading kicker={c.kicker} title={c.title} lead={c.lead}/>
      <div className="deck-inclusion-board">
        {c.included.map((item,index)=><div key={item}><span>{index<3?<FileImage/>:<HeartPulse/>}</span><p>{item}</p><Check/></div>)}
      </div>
    </section>
    <section className="deck-section deck-pricing-split">
      <article className="deck-fair-use"><span className="deck-mini-kicker">{c.fairKicker}</span><h2>{c.fairTitle}</h2><p>{c.fairBody}</p><div className="deck-fair-signal"><Activity/><span>NORMAL CLINICAL USE</span><b>∞</b></div></article>
      <article className="deck-annual"><span className="deck-mini-kicker">{c.annualKicker}</span><h2>{c.annualTitle}</h2><p>{c.annualBody}</p><div className="deck-months">{Array.from({length:12},(_,i)=><span className={i>9?"included":""} key={i}><b>{i+1}</b><small>{i>9?c.includedWord:c.paid}</small></span>)}</div></article>
    </section>
    <section className="deck-section deck-access-section">
      <DeckHeading kicker={c.accessKicker} title={c.accessTitle}/>
      <div className="deck-access-flow">{c.accessItems.map(([title,body],index)=><article key={title}><span>0{index+1}</span><strong>{title}</strong><p>{body}</p></article>)}</div>
      <p className="deck-access-note"><CircleAlert size={16}/>{c.accessNote}</p>
    </section>
  </div>;
}

function SafetyDeck({ lang }: { lang: Lang }) {
  const c = TEXT[lang].safety;
  return <div className="page-deck page-deck-safety">
    <section className="deck-section deck-claims-section">
      <DeckHeading kicker={c.kicker} title={c.title} lead={c.lead}/>
      <div className="deck-claims-grid">
        <article className="safe"><span><ShieldCheck/>{c.say}</span>{c.sayItems.map(item=><p key={item}><Check/>{item}</p>)}</article>
        <article className="unsafe"><span><CircleAlert/>{c.dont}</span>{c.dontItems.map(item=><p key={item}><span>×</span>{item}</p>)}</article>
      </div>
    </section>
    <section className="deck-section deck-human-section">
      <div className="deck-human-copy"><DeckHeading kicker={c.humanKicker} title={c.humanTitle} lead={c.humanBody}/><a href={WHO_AI} target="_blank" rel="noreferrer">WHO · Ethics and governance of AI for health <ExternalLink size={13}/></a></div>
      <div className="deck-human-gate">{c.humanFlow.map(([num,label],index)=><div key={num}><b>{num}</b><span>{label}</span>{index<c.humanFlow.length-1&&<ArrowRight/>}</div>)}</div>
    </section>
    <section className="deck-section deck-imaging-section">
      <div className="deck-imaging-mark"><Stethoscope/><Radar/></div>
      <div><span className="deck-mini-kicker">{c.imagingKicker}</span><h2>{c.imagingTitle}</h2><p>{c.imagingBody}</p><a href={ADA_RADIOGRAPHS} target="_blank" rel="noreferrer">{c.source} · ADA / AAOMR <ExternalLink size={13}/></a></div>
      <p className="deck-safety-foot"><ShieldCheck size={16}/>{c.safetyFoot}</p>
    </section>
  </div>;
}

function AboutDeck({ lang }: { lang: Lang }) {
  const c = TEXT[lang].about;
  return <div className="page-deck page-deck-about">
    <section className="deck-section deck-about-story">
      <DeckHeading kicker={c.kicker} title={c.title} lead={c.lead}/>
      <blockquote>{c.principle}</blockquote>
    </section>
    <section className="deck-section deck-team-section" id="team">
      <DeckHeading kicker={c.teamKicker} title={c.teamTitle}/>
      <div className="deck-team-grid">
        <article id="typhon-namira"><div className="deck-person-monogram">TN</div><span>{c.typhonRole}</span><h3>Typhon Namira</h3><p>{c.typhonBody}</p><div className="deck-person-links"><a href={TYPHON_LINKEDIN} target="_blank" rel="noreferrer">{c.publicProfile}<ExternalLink/></a><a href={PULSEMEAL_ABOUT} target="_blank" rel="noreferrer">{c.publicSource}<ExternalLink/></a></div></article>
        <article id="van-arzoyan"><div className="deck-person-monogram">VA</div><span>{c.vanRole}</span><h3>Van Arzoyan</h3><p>{c.vanBody}</p><div className="deck-tech-line"><BrainCircuit/><span>AI model fine-tuning</span></div></article>
      </div>
    </section>
    <section className="deck-section deck-contact-section" id="contact">
      <div className="deck-contact-copy"><DeckHeading kicker={c.contactKicker} title={c.contactTitle} lead={c.contactNote}/></div>
      <div className="deck-contact-board">
        <a href="mailto:teta2support@gmail.com"><Mail/><span><small>{c.email}</small><strong>teta2support@gmail.com</strong></span><ArrowRight/></a>
        <a href="tel:+37493700251"><Phone/><span><small>{c.phone}</small><strong>+374 93 700251</strong></span><ArrowRight/></a>
        <a href={WHATSAPP} target="_blank" rel="noreferrer"><MessageCircle/><span><small>{c.whatsapp}</small><strong>+374 93 700251</strong></span><ExternalLink/></a>
        <div><MessageCircle/><span><small>{c.telegram}</small><strong>+374 93 700251</strong></span><i>Telegram</i></div>
        <a className="wide" href={MAP_ADDRESS} target="_blank" rel="noreferrer"><MapPin/><span><small>{c.office}</small><strong>{c.address}</strong></span><ExternalLink/></a>
      </div>
    </section>
  </div>;
}

function DeckHeading({ kicker, title, lead }: { kicker: string; title: string; lead?: string }) {
  return <header className="deck-heading"><span className="deck-kicker"><Sparkles size={14}/>{kicker}</span><h2>{title}</h2>{lead&&<p>{lead}</p>}</header>;
}

function currentLang(): Lang {
  const value = localStorage.getItem("teta2-product-language") ?? localStorage.getItem("teta2-v4-language");
  return value === "hy" || value === "ru" ? value : "en";
}

function currentRoute(): DeckRoute | null {
  const path = window.location.pathname as DeckRoute;
  return ["/product","/how-it-works","/pricing","/clinical-safety","/about"].includes(path) ? path : null;
}

function contentFor(route: DeckRoute, lang: Lang) {
  if (route === "/product") return <ProductDeck lang={lang}/>;
  if (route === "/how-it-works") return <HowDeck lang={lang}/>;
  if (route === "/pricing") return <PricingDeck lang={lang}/>;
  if (route === "/clinical-safety") return <SafetyDeck lang={lang}/>;
  return <AboutDeck lang={lang}/>;
}

export function PageDeckSections() {
  const [route, setRoute] = useState<DeckRoute | null>(() => currentRoute());
  const [lang, setLang] = useState<Lang>(() => currentLang());
  const [host, setHost] = useState<HTMLElement | null>(null);
  const key = useMemo(() => `${route ?? "none"}:${lang}`, [route, lang]);

  useEffect(() => {
    const onRoute = () => setRoute(currentRoute());
    const onLanguage = (event: Event) => {
      const next = (event as CustomEvent<Lang>).detail;
      setLang(next === "hy" || next === "ru" ? next : "en");
    };
    window.addEventListener("popstate", onRoute);
    window.addEventListener("teta2-language-change", onLanguage);
    return () => { window.removeEventListener("popstate", onRoute); window.removeEventListener("teta2-language-change", onLanguage); };
  }, []);

  useEffect(() => {
    let observer: MutationObserver | null = null;
    let cancelled = false;
    document.getElementById("teta2-page-deck-root")?.remove();
    setHost(null);
    if (!route) return;

    const mount = () => {
      if (cancelled) return true;
      const main = document.querySelector<HTMLElement>(".product-marketing-page");
      if (!main) return false;
      let node = document.getElementById("teta2-page-deck-root") as HTMLElement | null;
      if (!node) {
        node = document.createElement("div");
        node.id = "teta2-page-deck-root";
        const finalCta = main.querySelector(":scope > .product-final-cta");
        if (finalCta) main.insertBefore(node, finalCta);
        else main.appendChild(node);
      }
      setHost(node);
      return true;
    };

    if (!mount()) {
      observer = new MutationObserver(() => { if (mount()) observer?.disconnect(); });
      observer.observe(document.getElementById("root") ?? document.body,{childList:true,subtree:true});
    }
    return () => { cancelled = true; observer?.disconnect(); document.getElementById("teta2-page-deck-root")?.remove(); };
  }, [route, key]);

  return route && host ? createPortal(contentFor(route,lang), host) : null;
}
