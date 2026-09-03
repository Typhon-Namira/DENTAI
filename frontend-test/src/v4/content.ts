export type Lang = "en" | "hy";

export const copy = {
  en: {
    brand: { name: "Teta2", tagline: "Teeth Evaluation & Treatment AI Assistant" },
    nav: {
      platform: "Platform", workspace: "AI Workspace", recall: "Smart Recall", radar: "Radar AI",
      security: "Security", pricing: "Pricing", login: "Login", register: "Get Started"
    },
    home: {
      eyebrow: "AI dental intelligence for clinical teams",
      title: "Teeth Evaluation & Treatment AI Assistant",
      lead: "Teta2 brings OPG analysis, tooth-level clinical records, follow-up workflows and Radar AI into one clinical platform designed around dentist review.",
      primary: "Get Started", secondary: "Explore AI Workspace",
      proof1: "9 verified ONNX model artifacts", proof2: "Clinician review required", proof3: "Tenant-isolated clinic data",
      sectionKicker: "One platform, four connected workflows",
      sectionTitle: "From radiograph to longitudinal care — without losing clinical context.",
      closingTitle: "Build the next layer of your clinic workflow.",
      closingCopy: "Start with one real clinic workflow, validate it with your team, and expand from there."
    },
    product: {
      eyebrow: "Platform overview", title: "Clinical AI, longitudinal records, recall and growth intelligence in one system.",
      lead: "Teta2 separates the responsibilities that should be separate — imaging, clinical records, communication and opportunity intelligence — while keeping them connected to the same clinic context.",
      cards: [
        ["AI Workspace", "Upload supported dental radiographs, request DENTAI V5 analysis, review findings and preserve the result in the patient record."],
        ["Structured tooth records", "Patient profiles retain X-rays, analyses, reviewed findings, visits, future-risk records, care timeline items and follow-ups."],
        ["Smart Recall", "Follow-up records and WhatsApp outreach keep care plans connected to the next patient interaction."],
        ["Radar AI", "Radar sources, runtime health, opportunities, scores and outcomes give the clinic a separate workflow for demand intelligence."]
      ]
    },
    workspace: {
      eyebrow: "AI Workspace", title: "Review OPG findings inside the clinical workflow.",
      lead: "The current backend accepts JPEG, PNG, WebP and DICOM uploads, stores them privately, creates AI analysis jobs and returns structured findings for clinician review.",
      steps: [["1", "Upload", "Attach a supported dental radiograph to an authorized patient."], ["2", "Analyze", "Create a DENTAI V5 analysis job and let the AI worker process it."], ["3", "Review", "Inspect findings, confidence and provenance; confirm or reject findings clinically."], ["4", "Preserve", "Keep the reviewed result with the patient profile for future visits."]],
      callout: "AI-assisted clinical decision support. Teta2 does not replace dentist diagnosis or treatment decisions."
    },
    recall: {
      eyebrow: "Smart Recall", title: "Turn reviewed clinical context into the next patient action.",
      lead: "Teta2 patient profiles include visits, future-risk records, future-care items and follow-ups. WhatsApp outreach can be connected to the same patient context for recall and follow-up communication.",
      cards: [["Follow-up timeline", "Track due dates, priority, status and the responsible doctor."], ["Longitudinal record", "Keep visits, X-rays, AI analyses and reviewed findings together."], ["WhatsApp outreach", "Connect the clinic sender, save a patient WhatsApp number and manage outreach records."], ["Clinical continuity", "Return to the same tooth-level context when the patient comes back."]]
    },
    radar: {
      eyebrow: "Radar AI", title: "A separate intelligence workflow for dental demand signals.",
      lead: "Radar AI manages configured sources, collector runtime health, scored opportunities and outcome feedback. It is intentionally separated from patient clinical records until the clinic chooses to act.",
      cards: [["Sources", "Configure and monitor supported Radar sources and their collection status."], ["Opportunity scoring", "Review tier, platform, language, location and score fields returned by the Radar backend."], ["Runtime health", "See active sources, due sources, unhealthy sources and collector readiness."], ["Outcome loop", "Record opportunity outcomes so the workflow can be calibrated against real results."]]
    },
    security: {
      eyebrow: "Security architecture", title: "Clinical data is isolated by clinic and access is role-aware.",
      lead: "The current backend uses a control-plane clinic registry plus separate tenant database connections, authenticated clinic context, private X-ray storage and audit logging.",
      cards: [["Tenant isolation", "Clinic registry entries resolve to encrypted tenant database URLs; clinical records live in the clinic database."], ["Private imaging", "X-rays are stored through the configured object-storage provider and accessed with authorized, time-limited download flows."], ["Role-aware access", "Director, Manager and Doctor roles have different branch and patient scopes in the API."], ["Audit trail", "Authentication, X-ray access, patient operations and other sensitive actions are recorded through the audit system."]],
      note: "Teta2 does not currently claim public HIPAA, GDPR or ISO certification in the repository. The frontend therefore does not present those badges."
    },
    pricing: {
      eyebrow: "Commercial access", title: "Public pricing is not defined in the current product configuration.",
      lead: "The repository contains package and usage models for clinic administration, but it does not define a verified public price list. We keep this page factual until commercial plans are finalized.",
      primary: "Start clinic onboarding", note: "No price or subscription claim is shown here until it exists in the backend or approved commercial configuration."
    },
    auth: {
      loginTitle: "Sign in to your clinic", loginCopy: "Use the clinic slug and credentials provisioned for your clinic.",
      slug: "Clinic slug", identifier: "Email or username", password: "Password", signIn: "Sign in securely", signingIn: "Signing in…",
      registerTitle: "Clinic onboarding", registerCopy: "The frontend is ready for clinic registration, but the current backend does not yet expose a public self-service provisioning endpoint.",
      clinicName: "Clinic name", city: "City", director: "Director name", email: "Work email", phone: "Phone", branches: "Branches", submit: "Provisioning API required",
      back: "Back to Teta2"
    },
    app: {
      morning: "Good morning", sub: "Let's analyze and plan the best care for your patients.",
      workspace: "AI Workspace", patients: "My Patients", xrays: "X-rays", followups: "Follow-ups", radar: "Radar AI", outreach: "Outreach", settings: "Settings",
      recentPatients: "Recent Patients", recentAnalyses: "Recent Analyses", schedule: "Today's Schedule", viewAll: "View all",
      drop: "Drag & drop your OPG or dental X-ray here", or: "or", upload: "Upload File", takePhoto: "Take Photo", gallery: "From Gallery",
      supported: "JPEG, PNG, WebP, DICOM — server upload limit applies", warning: "AI results support clinical decision-making and require dentist review.",
      noPatients: "No patients are available for this account.", noAnalyses: "No analyses yet.", noFollowups: "No follow-ups available.",
      selectPatient: "Select patient", runAnalysis: "Run DENTAI V5 Analysis", processing: "Processing…", findings: "Findings", review: "Clinical review", confirmed: "Confirmed", rejected: "Rejected", pending: "Pending"
    },
    admin: {
      title: "Platform Control Center", sub: "Clinic, subscription and payment controls require a dedicated platform-admin backend API.",
      overview: "Overview", clinics: "Clinics", subscriptions: "Subscriptions", payments: "Payments", plans: "Plans", activity: "Activity", settings: "Settings",
      total: "Total Clinics", active: "Active Subscriptions", pending: "Pending Payments", mrr: "Monthly Recurring Revenue",
      unavailable: "Platform admin data is not available from the current backend.", unavailableCopy: "No all-clinic registry, payment approval or platform-subscription endpoint is exposed today. This UI is intentionally empty rather than populated with invented clinics, revenue or payments."
    }
  },
  hy: {
    brand: { name: "Teta2", tagline: "Ատամների գնահատման և բուժման AI օգնական" },
    nav: { platform: "Հարթակ", workspace: "AI Workspace", recall: "Smart Recall", radar: "Radar AI", security: "Անվտանգություն", pricing: "Գնագոյացում", login: "Մուտք", register: "Սկսել" },
    home: {
      eyebrow: "AI ստոմատոլոգիական հարթակ կլինիկական թիմերի համար", title: "Ատամների գնահատման և բուժման AI օգնական",
      lead: "Teta2-ը մեկ կլինիկական հարթակում միավորում է OPG վերլուծությունը, ատամ առ ատամ գրառումները, follow-up հոսքերը և Radar AI-ը՝ բժշկի պարտադիր վերանայմամբ։",
      primary: "Սկսել", secondary: "Դիտել AI Workspace-ը", proof1: "9 հաստատված ONNX մոդելի artifact", proof2: "Բժշկի վերանայում պարտադիր է", proof3: "Կլինիկաների տվյալները tenant-ով մեկուսացված են",
      sectionKicker: "Մեկ հարթակ, չորս կապակցված հոսք", sectionTitle: "Ռենտգենից մինչև երկարաժամկետ խնամք՝ առանց կլինիկական համատեքստը կորցնելու։", closingTitle: "Ստեղծեք ձեր կլինիկայի աշխատանքի հաջորդ շերտը։", closingCopy: "Սկսեք մեկ իրական կլինիկական հոսքից, ստուգեք այն թիմի հետ և հետո ընդլայնեք։"
    },
    product: {
      eyebrow: "Հարթակի ընդհանուր տեսք", title: "Կլինիկական AI, երկարաժամկետ գրառումներ, recall և աճի intelligence՝ մեկ համակարգում։",
      lead: "Teta2-ը առանձնացնում է imaging-ը, կլինիկական գրառումները, հաղորդակցությունն ու opportunity intelligence-ը, բայց պահպանում է դրանք նույն կլինիկայի համատեքստում։",
      cards: [["AI Workspace", "Վերբեռնեք աջակցվող ռենտգեն, գործարկեք DENTAI V5 վերլուծությունը և պահպանեք արդյունքը պացիենտի գրառումներում։"], ["Ատամ առ ատամ գրառումներ", "Պացիենտի պրոֆիլը պահպանում է X-ray-երը, AI վերլուծությունները, բժշկի կողմից վերանայված finding-ները, այցերն ու follow-up-ները։"], ["Smart Recall", "Follow-up գրառումներն ու WhatsApp outreach-ը կապում են խնամքի պլանը հաջորդ այցի հետ։"], ["Radar AI", "Աղբյուրները, runtime health-ը, opportunity-ները, score-ներն ու outcome-ները կազմում են առանձին պահանջարկի intelligence հոսք։"]]
    },
    workspace: {
      eyebrow: "AI Workspace", title: "Վերանայեք OPG finding-ները հենց կլինիկական աշխատանքային հոսքում։",
      lead: "Ներկա backend-ը ընդունում է JPEG, PNG, WebP և DICOM ֆայլեր, պահում է դրանք մասնավոր storage-ում, ստեղծում է AI analysis job և վերադարձնում structured finding-ներ բժշկի վերանայման համար։",
      steps: [["1", "Վերբեռնում", "Կցեք աջակցվող ռենտգենը թույլատրված պացիենտին։"], ["2", "Վերլուծություն", "Ստեղծեք DENTAI V5 analysis job և թողեք AI worker-ին մշակել այն։"], ["3", "Վերանայում", "Դիտեք finding-ները, confidence-ը և provenance-ը, ապա հաստատեք կամ մերժեք կլինիկականորեն։"], ["4", "Պահպանում", "Պահեք վերանայված արդյունքը պացիենտի պրոֆիլում հաջորդ այցերի համար։"]],
      callout: "AI-ն կլինիկական որոշման աջակցման գործիք է և չի փոխարինում բժշկի ախտորոշմանը կամ բուժման որոշմանը։"
    },
    recall: {
      eyebrow: "Smart Recall", title: "Վերանայված կլինիկական համատեքստը վերածեք հաջորդ գործողության։",
      lead: "Teta2-ի պացիենտի պրոֆիլում կան այցեր, future-risk գրառումներ, future-care տարրեր և follow-up-ներ։ WhatsApp outreach-ը կարող է աշխատել նույն պացիենտի համատեքստով։",
      cards: [["Follow-up ժամանակագիծ", "Հետևեք due date-ին, priority-ին, status-ին և պատասխանատու բժշկին։"], ["Երկարաժամկետ գրառում", "Միասին պահեք այցերը, X-ray-երը, AI վերլուծությունները և վերանայված finding-ները։"], ["WhatsApp outreach", "Միացրեք կլինիկայի sender-ը, պահեք պացիենտի WhatsApp համարը և կառավարեք outreach գրառումները։"], ["Կլինիկական շարունակականություն", "Պացիենտի վերադարձի ժամանակ շարունակեք նույն ատամ առ ատամ համատեքստից։"]]
    },
    radar: {
      eyebrow: "Radar AI", title: "Առանձին intelligence հոսք՝ ստոմատոլոգիական պահանջարկի ազդակների համար։",
      lead: "Radar AI-ը կառավարում է source-երը, collector runtime health-ը, scored opportunity-ները և outcome feedback-ը։ Այն առանձնացված է պացիենտի կլինիկական գրառումներից մինչև կլինիկան որոշի գործել։",
      cards: [["Աղբյուրներ", "Կարգավորեք և վերահսկեք Radar source-երը ու collection status-ը։"], ["Opportunity scoring", "Դիտեք tier, platform, language, location և score դաշտերը, որոնք վերադարձնում է Radar backend-ը։"], ["Runtime health", "Տեսեք active, due, unhealthy source-երը և collector readiness-ը։"], ["Outcome loop", "Գրանցեք opportunity outcome-ները՝ իրական արդյունքների հիման վրա calibration-ի համար։"]]
    },
    security: {
      eyebrow: "Անվտանգության ճարտարապետություն", title: "Կլինիկական տվյալները մեկուսացված են ըստ կլինիկայի, իսկ մուտքը կախված է դերից։",
      lead: "Ներկա backend-ը օգտագործում է control-plane clinic registry, առանձին tenant database կապեր, authenticated clinic context, private X-ray storage և audit logging։",
      cards: [["Tenant մեկուսացում", "Clinic registry-ն լուծում է encrypted tenant database URL-ները, իսկ կլինիկական տվյալները պահվում են clinic database-ում։"], ["Մասնավոր imaging", "X-ray-երը պահվում են configured object storage-ում և հասանելի են authorization-ով ու ժամանակավոր download flow-ով։"], ["Role-aware access", "Director, Manager և Doctor դերերը API-ում ունեն տարբեր branch և patient scope-եր։"], ["Audit trail", "Authentication-ը, X-ray access-ը և այլ զգայուն գործողություններ գրանցվում են audit համակարգում։"]],
      note: "Repository-ում ներկայում չկա հրապարակային HIPAA, GDPR կամ ISO certification claim, ուստի frontend-ը նման badge-եր չի ցուցադրում։"
    },
    pricing: {
      eyebrow: "Առևտրային հասանելիություն", title: "Ներկա product configuration-ում հաստատված հրապարակային գներ չկան։",
      lead: "Repository-ում կան package և usage մոդելներ clinic administration-ի համար, բայց չկա հաստատված հրապարակային price list։ Մինչ commercial plan-ների հաստատումը էջը պահում ենք փաստացի։",
      primary: "Սկսել clinic onboarding", note: "Գնի կամ subscription-ի մասին չհաստատված claim այստեղ չի ցուցադրվում։"
    },
    auth: {
      loginTitle: "Մուտք գործեք ձեր կլինիկա", loginCopy: "Օգտագործեք ձեր կլինիկայի provision արված slug-ն ու credentials-ը։", slug: "Clinic slug", identifier: "Էլ․ փոստ կամ օգտանուն", password: "Գաղտնաբառ", signIn: "Անվտանգ մուտք", signingIn: "Մուտք…",
      registerTitle: "Clinic onboarding", registerCopy: "Frontend-ը պատրաստ է clinic registration-ի համար, բայց ներկա backend-ը դեռ չունի public self-service provisioning endpoint։", clinicName: "Կլինիկայի անվանում", city: "Քաղաք", director: "Տնօրենի անուն", email: "Աշխատանքային էլ․ փոստ", phone: "Հեռախոս", branches: "Մասնաճյուղեր", submit: "Provisioning API է անհրաժեշտ", back: "Վերադառնալ Teta2"
    },
    app: {
      morning: "Բարի լույս", sub: "Եկեք վերլուծենք և պլանավորենք լավագույն խնամքը ձեր պացիենտների համար։", workspace: "AI Workspace", patients: "Իմ պացիենտները", xrays: "Ռենտգեններ", followups: "Follow-ups", radar: "Radar AI", outreach: "Outreach", settings: "Կարգավորումներ",
      recentPatients: "Վերջին պացիենտները", recentAnalyses: "Վերջին վերլուծությունները", schedule: "Այսօրվա պլանը", viewAll: "Դիտել բոլորը", drop: "Քաշեք և թողեք OPG կամ dental X-ray-ը այստեղ", or: "կամ", upload: "Վերբեռնել ֆայլ", takePhoto: "Նկարել", gallery: "Պատկերասրահից", supported: "JPEG, PNG, WebP, DICOM — գործում է server upload limit-ը", warning: "AI արդյունքները աջակցում են կլինիկական որոշմանը և պահանջում են բժշկի վերանայում։", noPatients: "Այս հաշվի համար պացիենտներ չկան։", noAnalyses: "Վերլուծություններ դեռ չկան։", noFollowups: "Follow-up-ներ չկան։", selectPatient: "Ընտրել պացիենտ", runAnalysis: "Գործարկել DENTAI V5", processing: "Մշակվում է…", findings: "Finding-ներ", review: "Կլինիկական վերանայում", confirmed: "Հաստատված", rejected: "Մերժված", pending: "Սպասող"
    },
    admin: {
      title: "Platform Control Center", sub: "Clinic, subscription և payment control-ների համար անհրաժեշտ է dedicated platform-admin backend API։", overview: "Ամփոփում", clinics: "Կլինիկաներ", subscriptions: "Subscription-ներ", payments: "Վճարումներ", plans: "Փաթեթներ", activity: "Գործողություններ", settings: "Կարգավորումներ", total: "Բոլոր կլինիկաները", active: "Ակտիվ subscription-ներ", pending: "Սպասող վճարումներ", mrr: "Ամսական recurring revenue", unavailable: "Ներկա backend-ից platform admin data հասանելի չէ։", unavailableCopy: "Այս պահին չկա all-clinic registry, payment approval կամ platform-subscription endpoint։ UI-ը դիտավորյալ դատարկ է և չի ցուցադրում հորինված կլինիկաներ, revenue կամ payments։"
    }
  }
} as const;

export function t(lang: Lang) { return copy[lang]; }
