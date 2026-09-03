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
      lead: "Teta2 keeps imaging, clinical records, communication and opportunity intelligence as distinct workflows while connecting them through the same clinic context.",
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
      lead: "Radar AI manages configured sources, collector runtime health, scored opportunities and outcome feedback. It stays separate from patient clinical records until the clinic chooses to act.",
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
      back: "Back to Teta2",
      registerFacts: ["Tenant database provisioning", "Director account creation", "Allowed-origin configuration"]
    },
    app: {
      morning: "Good morning", sub: "Let's analyze and plan the best care for your patients.",
      workspace: "AI Workspace", patients: "My Patients", xrays: "X-rays", followups: "Follow-ups", radar: "Radar AI", outreach: "Outreach", settings: "Settings",
      recentPatients: "Recent Patients", recentAnalyses: "Recent Analyses", schedule: "Today's Schedule", viewAll: "View all",
      drop: "Drag & drop your OPG or dental X-ray here", or: "or", upload: "Upload File", takePhoto: "Take Photo", gallery: "From Gallery",
      supported: "JPEG, PNG, WebP, DICOM — server upload limit applies", warning: "AI results support clinical decision-making and require dentist review.",
      noPatients: "No patients are available for this account.", noAnalyses: "No analyses yet.", noFollowups: "No follow-ups available.",
      selectPatient: "Select patient", selectXray: "Select X-ray", runAnalysis: "Run DENTAI V5 Analysis", processing: "Processing…", findings: "Findings", review: "Clinical review", confirmed: "Confirmed", rejected: "Rejected", pending: "Pending",
      branchScope: "branch scope", patientRecordsSubtitle: "Authorized patient records and longitudinal clinical context.",
      labels: { xrays: "X-rays", analyses: "Analyses", findings: "Findings", activeSources: "Active sources", dueSources: "Due sources", unhealthySources: "Unhealthy sources", opportunities: "Opportunities", whatsappConnection: "WhatsApp connection", whatsapp: "WhatsApp", phone: "Phone", email: "Email", authenticatedContext: "Authenticated context", clinicId: "Clinic ID", role: "Role", backend: "Backend", branchScope: "Branch scope" },
      messages: { noRadar: "No Radar opportunities returned by the backend.", noSender: "No sender returned by the backend.", backendHealth: "Health and readiness are checked through the configured API endpoint." }
    },
    visuals: {
      windowTitle: "Teta2 · OPG Analysis", workspace: "AI Workspace", patients: "Patients", xrays: "X-rays", followups: "Follow-ups", radar: "Radar AI",
      sourceImage: "Source OPG radiograph", sourceImageText: "Real panoramic radiograph used for the product preview", reviewContext: "Clinical review context", reviewContextText: "No synthetic patient result is shown here",
      reviewStates: "Review states", reviewed: "Reviewed finding", reviewRequired: "Review required", toothContext: "Tooth context",
      recallTitle: "Smart Recall", dueFollowups: "Due follow-ups", loadedFromClinic: "Loaded from clinic data", patientRecord: "Patient record", timeline: "Timeline", timelineItems: "Visits · X-rays · Findings", finding: "Finding", followup: "Follow-up", outreach: "Outreach", returnVisit: "Return visit",
      radarTitle: "Radar AI", sources: "Sources", runtimeHealth: "Runtime health", opportunities: "Opportunities", outcomes: "Outcomes", queue: "Opportunity queue", queueFields1: "Tier · Platform · Score", queueFields2: "Location · Language", queueFields3: "Status · Outcome",
      controlPlane: "Control plane", clinicRegistry: "Clinic registry", encryptedDsn: "Encrypted tenant DSN", authenticatedContext: "Resolved in authenticated clinic context", clinicDatabase: "Clinic database", clinicalRecords: "Clinical records", privateStorage: "Private object storage for X-rays"
    },
    misc: {
      explore: "Explore", access: "Access", footerDecisionSupport: "AI-assisted clinical decision support", languageFooter: "You can change the interface language later",
      architectureTitle: "How the platform is organized", aiAnalysis: "AI analysis", structuredInference: "Structured inference and review", patientProfile: "Patient profile", longitudinalContext: "Longitudinal clinical context", careContinuity: "Care continuity and outreach", separateOpportunity: "Separate opportunity workflow",
      workflowTitle: "A clinical workflow with explicit review points.", journeyTitle: "From reviewed finding to the next visit", aiReview: "AI review", clinicalContext: "Clinical context", returnVisit: "Return visit",
      clinicianLoop: "Clinician in the loop", tenantRecords: "Tenant-isolated records", privateXray: "Private X-ray storage", auditedActions: "Audited sensitive actions",
      admin: "ADMIN"
    },
    admin: {
      title: "Platform Control Center", sub: "Clinic, subscription and payment controls require a dedicated platform-admin backend API.",
      overview: "Overview", clinics: "Clinics", subscriptions: "Subscriptions", payments: "Payments", plans: "Plans", activity: "Activity", settings: "Settings",
      total: "Total Clinics", active: "Active Subscriptions", pending: "Pending Payments", mrr: "Monthly Recurring Revenue",
      unavailable: "Platform admin data is not available from the current backend.", unavailableCopy: "No all-clinic registry, payment approval or platform-subscription endpoint is exposed today. This UI is intentionally empty rather than populated with invented clinics, revenue or payments."
    }
  },
  hy: {
    brand: { name: "Teta2", tagline: "Ատամնաբուժական գնահատման և բուժման AI օգնական" },
    nav: { platform: "Հարթակ", workspace: "AI աշխատանքային տարածք", recall: "Հետադարձ այցեր", radar: "Radar AI", security: "Անվտանգություն", pricing: "Գնային պայմաններ", login: "Մուտք", register: "Սկսել" },
    home: {
      eyebrow: "AI ստոմատոլոգիական հարթակ կլինիկական թիմերի համար", title: "Ատամնաբուժական գնահատման և բուժման AI օգնական",
      lead: "Teta2-ը մեկ կլինիկական հարթակում միավորում է OPG վերլուծությունը, ատամային մակարդակի կլինիկական գրառումները, հետադարձ այցերի կառավարումը և Radar AI-ը՝ բժշկի պարտադիր վերահսկմամբ։",
      primary: "Սկսել", secondary: "Դիտել AI աշխատանքային տարածքը", proof1: "9 հաստատված ONNX մոդելի ֆայլ", proof2: "Բժշկի վերանայումը պարտադիր է", proof3: "Կլինիկաների տվյալները մեկուսացված են",
      sectionKicker: "Մեկ հարթակ, չորս փոխկապակցված աշխատանքային հոսք", sectionTitle: "Ռենտգեն պատկերից մինչև երկարաժամկետ խնամք՝ առանց կլինիկական համատեքստը կորցնելու։", closingTitle: "Ավելացրեք խելացի շերտ ձեր կլինիկայի աշխատանքին։", closingCopy: "Սկսեք մեկ իրական կլինիկական հոսքից, փորձարկեք այն ձեր թիմի հետ և ընդլայնեք ըստ կարիքի։"
    },
    product: {
      eyebrow: "Հարթակի ընդհանուր պատկերը", title: "Կլինիկական AI, երկարաժամկետ գրառումներ, հետադարձ այցեր և պահանջարկի վերլուծություն՝ մեկ համակարգում։",
      lead: "Teta2-ը պատկերների վերլուծությունը, կլինիկական գրառումները, հաղորդակցությունն ու պահանջարկի վերլուծությունը պահում է որպես առանձին, բայց փոխկապակցված աշխատանքային հոսքեր՝ նույն կլինիկայի համատեքստում։",
      cards: [["AI աշխատանքային տարածք", "Վերբեռնեք աջակցվող ատամնաբուժական ռենտգենը, գործարկեք DENTAI V5 վերլուծությունը, վերանայեք արդյունքները և պահեք դրանք պացիենտի քարտում։"], ["Ատամային կառուցվածքային գրառումներ", "Պացիենտի պրոֆիլում պահպանվում են ռենտգենները, AI վերլուծությունները, բժշկի կողմից վերանայված արդյունքները, այցերը, ապագա ռիսկերը, խնամքի տարրերն ու հետադարձ այցերը։"], ["Հետադարձ այցերի կառավարում", "Հետադարձ այցերի գրառումներն ու WhatsApp հաղորդակցությունը կապում են բուժման պլանը պացիենտի հաջորդ այցի հետ։"], ["Radar AI", "Radar-ի աղբյուրները, աշխատանքի վիճակը, հնարավորությունները, գնահատականներն ու արդյունքները կազմում են պահանջարկի վերլուծության առանձին հոսք։"]]
    },
    workspace: {
      eyebrow: "AI աշխատանքային տարածք", title: "Վերանայեք OPG արդյունքները հենց կլինիկական աշխատանքային հոսքի մեջ։",
      lead: "Ներկա backend-ը ընդունում է JPEG, PNG, WebP և DICOM ֆայլեր, պահում է դրանք մասնավոր պահոցում, ստեղծում է AI վերլուծության առաջադրանք և վերադարձնում կառուցվածքային արդյունքներ՝ բժշկի վերանայման համար։",
      steps: [["1", "Վերբեռնում", "Կցեք աջակցվող ատամնաբուժական ռենտգենը թույլատրված պացիենտի քարտին։"], ["2", "Վերլուծություն", "Ստեղծեք DENTAI V5 վերլուծության առաջադրանք և փոխանցեք այն AI worker-ին։"], ["3", "Բժշկական վերանայում", "Դիտեք արդյունքները, վստահության մակարդակն ու աղբյուրային տվյալները, ապա հաստատեք կամ մերժեք դրանք։"], ["4", "Պահպանում", "Պահեք բժշկի կողմից վերանայված արդյունքը պացիենտի պրոֆիլում՝ հետագա այցերի համար։"]],
      callout: "Teta2-ը կլինիկական որոշումների աջակցման գործիք է։ Այն չի փոխարինում բժշկի ախտորոշմանը կամ բուժման վերաբերյալ որոշմանը։"
    },
    recall: {
      eyebrow: "Հետադարձ այցերի կառավարում", title: "Վերանայված կլինիկական տվյալները վերածեք հաջորդ հստակ գործողության։",
      lead: "Teta2-ի պացիենտի պրոֆիլը ներառում է այցերը, ապագա ռիսկերի գրառումները, հետագա խնամքի տարրերն ու հետադարձ այցերը։ WhatsApp հաղորդակցությունը կարող է աշխատել նույն պացիենտի համատեքստով։",
      cards: [["Հետադարձ այցերի ժամանակագիծ", "Հետևեք նախատեսված ամսաթվին, առաջնահերթությանը, կարգավիճակին և պատասխանատու բժշկին։"], ["Երկարաժամկետ պացիենտի քարտ", "Միասին պահեք այցերը, ռենտգենները, AI վերլուծություններն ու բժշկի կողմից վերանայված արդյունքները։"], ["WhatsApp հաղորդակցություն", "Միացրեք կլինիկայի ուղարկող հաշիվը, պահեք պացիենտի WhatsApp համարը և կառավարեք հաղորդակցության պատմությունը։"], ["Կլինիկական շարունակականություն", "Պացիենտի վերադարձի ժամանակ շարունակեք նույն ատամային համատեքստից։"]]
    },
    radar: {
      eyebrow: "Radar AI", title: "Առանձին վերլուծական հոսք՝ ատամնաբուժական ծառայությունների պահանջարկի ազդակների համար։",
      lead: "Radar AI-ը կառավարում է կարգավորված աղբյուրները, հավաքիչների աշխատանքի վիճակը, գնահատված հնարավորություններն ու արդյունքների հետադարձ կապը։ Այն առանձին է պահվում պացիենտի կլինիկական գրառումներից մինչև կլինիկան որոշի գործել։",
      cards: [["Աղբյուրներ", "Կարգավորեք և վերահսկեք Radar-ի աջակցվող աղբյուրներն ու դրանց տվյալների հավաքման վիճակը։"], ["Հնարավորությունների գնահատում", "Դիտեք Radar backend-ի վերադարձած մակարդակը, հարթակը, լեզուն, տեղադրությունն ու գնահատականը։"], ["Աշխատանքի վիճակ", "Տեսեք ակտիվ, հերթագրված և խնդրահարույց աղբյուրները, ինչպես նաև հավաքիչների պատրաստվածությունը։"], ["Արդյունքների հետադարձ կապ", "Գրանցեք հնարավորությունների արդյունքները՝ համակարգի հետագա ճշգրտման համար։"]]
    },
    security: {
      eyebrow: "Անվտանգության ճարտարապետություն", title: "Կլինիկական տվյալները մեկուսացված են ըստ կլինիկայի, իսկ հասանելիությունը՝ ըստ օգտատիրոջ դերի։",
      lead: "Ներկա backend-ը օգտագործում է կառավարման clinic registry, առանձին tenant database կապեր, նույնականացված կլինիկայի համատեքստ, մասնավոր ռենտգեն պահոց և audit գրանցում։",
      cards: [["Կլինիկաների տվյալների մեկուսացում", "Clinic registry-ի գրառումները կապվում են կոդավորված tenant database URL-ներին, իսկ կլինիկական տվյալները պահվում են տվյալ կլինիկայի բազայում։"], ["Մասնավոր ռենտգեն պահոց", "Ռենտգենները պահվում են կարգավորված object storage-ում և հասանելի են միայն թույլատրված, ժամանակով սահմանափակված ներբեռնման հոսքով։"], ["Դերով պայմանավորված հասանելիություն", "Director, Manager և Doctor դերերը API-ում ունեն տարբեր մասնաճյուղային և պացիենտային հասանելիության սահմաններ։"], ["Գործողությունների գրանցում", "Նույնականացումը, ռենտգենների հասանելիությունը, պացիենտների գործողություններն ու այլ զգայուն քայլերը գրանցվում են audit համակարգում։"]],
      note: "Repository-ում ներկայում հրապարակային HIPAA, GDPR կամ ISO հավաստագրման հաստատված պնդում չկա, ուստի frontend-ը նման նշաններ չի ցուցադրում։"
    },
    pricing: {
      eyebrow: "Առևտրային հասանելիություն", title: "Ներկա արտադրանքի կարգավորումներում հաստատված հրապարակային գներ սահմանված չեն։",
      lead: "Repository-ում կան package և usage մոդելներ կլինիկայի կառավարման համար, սակայն հաստատված հրապարակային գնացուցակ չկա։ Մինչ առևտրային պայմանների հաստատումը այս էջում ցուցադրում ենք միայն փաստացի տեղեկություն։",
      primary: "Սկսել կլինիկայի գրանցման գործընթացը", note: "Գնի կամ բաժանորդագրության մասին չհաստատված որևէ պնդում այստեղ չի ցուցադրվում։"
    },
    auth: {
      loginTitle: "Մուտք գործեք ձեր կլինիկայի միջավայր", loginCopy: "Օգտագործեք ձեր կլինիկայի համար ստեղծված slug-ը և մուտքի տվյալները։", slug: "Կլինիկայի slug", identifier: "Էլ․ փոստ կամ օգտանուն", password: "Գաղտնաբառ", signIn: "Անվտանգ մուտք", signingIn: "Մուտք է կատարվում…",
      registerTitle: "Կլինիկայի գրանցում", registerCopy: "Frontend-ը պատրաստ է կլինիկայի գրանցման հոսքի համար, սակայն ներկա backend-ը դեռ չունի հանրային ինքնասպասարկման provisioning endpoint։", clinicName: "Կլինիկայի անվանում", city: "Քաղաք", director: "Տնօրենի անուն", email: "Աշխատանքային էլ․ փոստ", phone: "Հեռախոս", branches: "Մասնաճյուղերի քանակ", submit: "Անհրաժեշտ է provisioning API", back: "Վերադառնալ Teta2",
      registerFacts: ["Առանձին tenant database-ի ստեղծում", "Տնօրենի հաշվի ստեղծում", "Թույլատրված origin-ի կարգավորում"]
    },
    app: {
      morning: "Բարի լույս", sub: "Եկեք վերլուծենք տվյալները և պլանավորենք լավագույն խնամքը ձեր պացիենտների համար։", workspace: "AI աշխատանքային տարածք", patients: "Իմ պացիենտները", xrays: "Ռենտգեն պատկերներ", followups: "Հետադարձ այցեր", radar: "Radar AI", outreach: "Հաղորդակցություն", settings: "Կարգավորումներ",
      recentPatients: "Վերջին պացիենտները", recentAnalyses: "Վերջին վերլուծությունները", schedule: "Այսօրվա պլանը", viewAll: "Դիտել բոլորը", drop: "Քաշեք և թողեք OPG կամ ատամնաբուժական ռենտգեն պատկերը այստեղ", or: "կամ", upload: "Վերբեռնել ֆայլ", takePhoto: "Լուսանկարել", gallery: "Ընտրել պատկերասրահից", supported: "JPEG, PNG, WebP, DICOM — գործում է սերվերի վերբեռնման սահմանաչափը", warning: "AI արդյունքները աջակցում են կլինիկական որոշումների կայացմանը և պահանջում են բժշկի պարտադիր վերանայում։", noPatients: "Այս հաշվի համար հասանելի պացիենտներ չկան։", noAnalyses: "Վերլուծություններ դեռ չկան։", noFollowups: "Հետադարձ այցեր չկան։", selectPatient: "Ընտրել պացիենտ", selectXray: "Ընտրել ռենտգեն", runAnalysis: "Գործարկել DENTAI V5 վերլուծությունը", processing: "Մշակվում է…", findings: "Արդյունքներ", review: "Բժշկական վերանայում", confirmed: "Հաստատված", rejected: "Մերժված", pending: "Սպասող",
      branchScope: "մասնաճյուղային հասանելիություն", patientRecordsSubtitle: "Թույլատրված պացիենտների գրառումներ և երկարաժամկետ կլինիկական համատեքստ։",
      labels: { xrays: "Ռենտգեններ", analyses: "Վերլուծություններ", findings: "Արդյունքներ", activeSources: "Ակտիվ աղբյուրներ", dueSources: "Հերթագրված աղբյուրներ", unhealthySources: "Խնդրահարույց աղբյուրներ", opportunities: "Հնարավորություններ", whatsappConnection: "WhatsApp կապ", whatsapp: "WhatsApp", phone: "Հեռախոս", email: "Էլ․ փոստ", authenticatedContext: "Նույնականացված միջավայր", clinicId: "Կլինիկայի ID", role: "Դեր", backend: "Backend", branchScope: "Մասնաճյուղային հասանելիություն" },
      messages: { noRadar: "Backend-ը Radar-ի հնարավորություն չի վերադարձրել։", noSender: "Backend-ը ուղարկող հաշիվ չի վերադարձրել։", backendHealth: "Սերվերի առողջությունն ու պատրաստվածությունը ստուգվում են կարգավորված API endpoint-ի միջոցով։" }
    },
    visuals: {
      windowTitle: "Teta2 · OPG վերլուծություն", workspace: "AI աշխատանքային տարածք", patients: "Պացիենտներ", xrays: "Ռենտգեններ", followups: "Հետադարձ այցեր", radar: "Radar AI",
      sourceImage: "Սկզբնական OPG ռենտգեն", sourceImageText: "Ապրանքի ցուցադրման համար օգտագործվող իրական պանորամիկ ռենտգեն", reviewContext: "Բժշկական վերանայման միջավայր", reviewContextText: "Այստեղ չի ցուցադրվում հորինված պացիենտի արդյունք",
      reviewStates: "Վերանայման վիճակներ", reviewed: "Վերանայված արդյունք", reviewRequired: "Պահանջվում է վերանայում", toothContext: "Ատամային համատեքստ",
      recallTitle: "Հետադարձ այցերի կառավարում", dueFollowups: "Սպասվող հետադարձ այցեր", loadedFromClinic: "Բեռնվում է կլինիկայի իրական տվյալներից", patientRecord: "Պացիենտի քարտ", timeline: "Ժամանակագիծ", timelineItems: "Այցեր · Ռենտգեններ · Արդյունքներ", finding: "Արդյունք", followup: "Հետադարձ այց", outreach: "Հաղորդակցություն", returnVisit: "Վերադարձի այց",
      radarTitle: "Radar AI", sources: "Աղբյուրներ", runtimeHealth: "Աշխատանքի վիճակ", opportunities: "Հնարավորություններ", outcomes: "Արդյունքներ", queue: "Հնարավորությունների հերթ", queueFields1: "Մակարդակ · Հարթակ · Գնահատական", queueFields2: "Տեղադրություն · Լեզու", queueFields3: "Կարգավիճակ · Արդյունք",
      controlPlane: "Կառավարման շերտ", clinicRegistry: "Կլինիկաների registry", encryptedDsn: "Կոդավորված tenant DSN", authenticatedContext: "Բացվում է նույնականացված կլինիկայի համատեքստում", clinicDatabase: "Կլինիկայի տվյալների բազա", clinicalRecords: "Կլինիկական գրառումներ", privateStorage: "Ռենտգենների մասնավոր object storage"
    },
    misc: {
      explore: "Դիտել", access: "Մուտք", footerDecisionSupport: "AI աջակցությամբ կլինիկական որոշումների կայացում", languageFooter: "Միջերեսի լեզուն կարող եք փոխել նաև հետագայում",
      architectureTitle: "Ինչպես է կառուցված հարթակը", aiAnalysis: "AI վերլուծություն", structuredInference: "Կառուցվածքային վերլուծություն և բժշկական վերանայում", patientProfile: "Պացիենտի պրոֆիլ", longitudinalContext: "Երկարաժամկետ կլինիկական համատեքստ", careContinuity: "Խնամքի շարունակականություն և հաղորդակցություն", separateOpportunity: "Հնարավորությունների առանձին հոսք",
      workflowTitle: "Կլինիկական հոսք՝ հստակ բժշկական վերանայման փուլերով։", journeyTitle: "Վերանայված արդյունքից մինչև հաջորդ այց", aiReview: "AI արդյունքի վերանայում", clinicalContext: "Կլինիկական համատեքստ", returnVisit: "Վերադարձի այց",
      clinicianLoop: "Բժիշկը վերահսկում է արդյունքը", tenantRecords: "Կլինիկաների մեկուսացված գրառումներ", privateXray: "Ռենտգենների մասնավոր պահոց", auditedActions: "Զգայուն գործողությունների audit գրանցում",
      admin: "ԱԴՄԻՆ"
    },
    admin: {
      title: "Հարթակի կառավարման կենտրոն", sub: "Կլինիկաների, բաժանորդագրությունների և վճարումների կառավարման համար անհրաժեշտ է առանձին platform-admin backend API։", overview: "Ընդհանուր պատկեր", clinics: "Կլինիկաներ", subscriptions: "Բաժանորդագրություններ", payments: "Վճարումներ", plans: "Փաթեթներ", activity: "Գործողություններ", settings: "Կարգավորումներ", total: "Կլինիկաների քանակ", active: "Ակտիվ բաժանորդագրություններ", pending: "Սպասող վճարումներ", mrr: "Ամսական կրկնվող եկամուտ", unavailable: "Ներկա backend-ից հարթակի կառավարման տվյալներ հասանելի չեն։", unavailableCopy: "Այս պահին բացակայում են բոլոր կլինիկաների registry-ի, վճարումների հաստատման և հարթակի բաժանորդագրությունների endpoint-ները։ UI-ը դիտավորյալ չի լրացվում հորինված կլինիկաներով, եկամուտներով կամ վճարումներով։"
    }
  }
} as const;

export function t(lang: Lang) { return copy[lang]; }
