export type ProductLang = "en" | "hy";

export const PRODUCT_COPY = {
  en: {
    nav: { product: "Product", how: "How it works", pricing: "Pricing", safety: "Clinical & Safety", about: "About / Contact", login: "Sign in", access: "Request access" },
    hero: {
      eyebrow: "AI-powered OPG intelligence + patient follow-up",
      title: "Turn Every OPG Into Actionable Patient Follow-up.",
      lead: "AI-powered OPG analysis that helps dental clinics identify possible findings, organize patient records, and—through Teta2 Care—follow up with patients automatically.",
      primary: "Analyze an OPG",
      secondary: "See how it works",
      proof: ["AI-assisted possible findings", "Dentist review stays in control", "Care closes the follow-up loop"]
    },
    problem: {
      kicker: "From image to action",
      title: "An OPG should not end as a forgotten image.",
      body: "Teta2 turns the panoramic X-ray into a structured clinical workflow: possible findings, a smart patient file, and—on Care—a follow-up timeline that helps the clinic act before the patient disappears.",
      cards: [
        ["Understand faster", "Organize possible findings by tooth or region where the model supports it."],
        ["Keep the record", "Store OPGs, analyses and clinician review inside the patient’s smart dental file."],
        ["Follow through", "Care turns findings into follow-up actions, configured messages and patient-return tracking."]
      ]
    },
    workflow: {
      kicker: "Core workflow",
      title: "Scan → Understand → Record → Follow → Return",
      steps: [
        ["01", "Create patient", "Start a simple smart patient profile with essential contact and clinical context."],
        ["02", "Upload OPG", "Upload the patient’s panoramic X-ray into protected clinical storage."],
        ["03", "AI-assisted analysis", "Teta2 produces possible findings for dentist examination."],
        ["04", "Clinician review", "Review findings visually on the radiograph and confirm or reject them."],
        ["05", "Smart patient file", "Keep OPG, analysis and review history together in the patient record."],
        ["06", "Care follow-up", "Create problem/tooth-based follow-up timing from the clinical context."],
        ["07", "Patient message", "Send the configured follow-up message and track its delivery state."],
        ["08", "Patient return", "Track the follow-up state and act when the patient returns to the clinic."]
      ]
    },
    plans: {
      kicker: "Two focused plans",
      title: "Choose analysis only—or close the follow-up loop.",
      scan: { name: "Teta2 Scan", tagline: "See what’s hiding in the OPG.", outcome: "Scan → Understand → Record", features: ["Unlimited OPG analysis during the subscription month", "AI-assisted OPG analysis", "Possible findings", "Tooth/region organization where supported", "Visual highlighting on the OPG", "AI report", "Smart patient profile", "OPG history", "Analysis history"] },
      care: { name: "Teta2 Care", tagline: "Never lose a patient who needs follow-up.", outcome: "Scan → Understand → Record → Follow → Return", features: ["Everything in Teta2 Scan", "Smart follow-up", "Problem/tooth-based follow-up timing", "Automated patient messages", "Patient response tracking", "Recall management", "Follow-up dashboard", "Finding and treatment follow-up history", "Patient-return tracking"] }
    },
    safety: {
      kicker: "Clinical safety by design",
      title: "AI supports the dentist. It does not replace clinical judgment.",
      body: "Teta2 presents AI-assisted possible findings for professional examination. The clinician remains responsible for review, diagnosis and care decisions.",
      items: [
        ["Human in the loop", "Every possible finding stays reviewable by the dentist."],
        ["Protected clinical data", "Access control, encrypted storage and audit logging are part of the platform architecture."],
        ["Responsible claims", "Teta2 does not present model output as a definitive diagnosis or claim unvalidated diagnostic accuracy."]
      ]
    },
    pricing: {
      title: "Simple pricing for focused clinical value.",
      lead: "Both plans include unlimited OPG analysis for normal clinical use. Fair Use Policy applies to abnormal automated bulk processing or API abuse.",
      monthly: "month",
      annual: "Annual option: pay for 10 months and receive 12 months of access.",
      market: "Market",
      unlimited: "Unlimited OPG analysis",
      choose: "Request access"
    },
    about: {
      title: "Teta2 is built around one clinical loop.",
      lead: "We are building focused dental AI for OPG intelligence and patient follow-up—not a generic clinic CRM. For commercial access, use the Teta2 onboarding flow from this website.",
      principle: "Simple beats comprehensive. OPG stays at the center. Every AI finding should lead to a useful clinical workflow.",
      roadmap: ["Scan: reliable OPG upload, analysis, findings and patient record", "Care: follow-up engine, messaging, response tracking and patient return", "Clinical intelligence: stronger tooth mapping and longitudinal comparison after validation", "Growth add-ons only after the core product has traction"]
    },
    access: {
      title: "Request access to Teta2",
      lead: "Clinic onboarding is currently provisioned directly. Public self-service provisioning is not enabled yet.",
      note: "Choose Teta2 Scan or Teta2 Care during commercial onboarding. A clinic workspace must be provisioned before sign-in credentials can be issued.",
      login: "Already provisioned? Sign in"
    },
    clinic: {
      dashboard: "Dashboard", patients: "Patients", opg: "OPG Analysis", followups: "Follow-ups", messages: "Messages", settings: "Settings",
      dashboardTitle: "Clinical action dashboard", dashboardLead: "The OPG-to-follow-up loop, using live clinic data.",
      newPatient: "New patient", selectPatient: "Select a patient", upload: "Upload OPG", analyze: "Run AI-assisted analysis",
      possibleFinding: "possible finding", requiresExam: "Requires dentist examination",
      noPatient: "Select a patient to open the smart patient file.",
      noFollowups: "No follow-ups are currently visible for your scope.",
      messagesLead: "Patient follow-up messaging for the selected patient, using the clinic’s connected WhatsApp sender.",
      careRecord: "Smart Patient File", overview: "Overview", opgHistory: "OPG History", findings: "Possible Findings", timeline: "Follow-up", messageHistory: "Messages"
    }
  },
  hy: {
    nav: { product: "Արտադրանք", how: "Ինչպես է աշխատում", pricing: "Գներ", safety: "Կլինիկական անվտանգություն", about: "Մեր մասին / Կապ", login: "Մուտք", access: "Մուտքի հարցում" },
    hero: {
      eyebrow: "AI-ով OPG վերլուծություն + պացիենտի հետագա վերահսկում",
      title: "Յուրաքանչյուր OPG-ն վերածեք գործնական հետագա վերահսկման։",
      lead: "AI-ով OPG վերլուծություն, որը օգնում է կլինիկաներին հայտնաբերել հնարավոր արդյունքները, կազմակերպել պացիենտի տվյալները և Teta2 Care-ի միջոցով ավտոմատ շարունակել պացիենտի հետ կապը։",
      primary: "Վերլուծել OPG",
      secondary: "Ինչպես է աշխատում",
      proof: ["AI-ով աջակցվող հնարավոր հայտնաբերումներ", "Բժշկի վերահսկումը կենտրոնում է", "Care-ը փակում է հետագա վերահսկման շղթան"]
    },
    problem: {
      kicker: "Պատկերից դեպի գործողություն",
      title: "OPG-ն չպետք է ավարտվի որպես մոռացված պատկեր։",
      body: "Teta2-ը պանորամիկ ռենտգենը վերածում է կառուցվածքային կլինիկական ընթացքի՝ հնարավոր հայտնաբերումներ, խելացի պացիենտի քարտ և Care պլանում՝ հետագա վերահսկման ժամանակագիծ։",
      cards: [
        ["Ավելի արագ հասկանալ", "Հնարավոր արդյունքները կազմակերպվում են ըստ ատամի կամ շրջանի, որտեղ մոդելը դա աջակցում է։"],
        ["Պահպանել պատմությունը", "OPG-ները, վերլուծությունները և բժշկի վերանայումը պահվում են պացիենտի խելացի քարտում։"],
        ["Շարունակել վերահսկումը", "Care-ը հայտնաբերումները վերածում է հետագա գործողությունների, հաղորդագրությունների և վերադարձի վերահսկման։"]
      ]
    },
    workflow: {
      kicker: "Հիմնական ընթացք",
      title: "Սքան → Հասկանալ → Պահպանել → Հետևել → Վերադարձ",
      steps: [
        ["01", "Ստեղծել պացիենտ", "Ստեղծեք պարզ խելացի պացիենտի քարտ՝ հիմնական կոնտակտային և կլինիկական տվյալներով։"],
        ["02", "Վերբեռնել OPG", "Վերբեռնեք պացիենտի պանորամիկ ռենտգենը պաշտպանված կլինիկական պահոց։"],
        ["03", "AI-ով աջակցվող վերլուծություն", "Teta2-ը ներկայացնում է հնարավոր հայտնաբերումներ՝ ատամնաբույժի զննման համար։"],
        ["04", "Բժշկի վերանայում", "Տեսողականորեն ստուգեք արդյունքները ռենտգենի վրա և հաստատեք կամ մերժեք դրանք։"],
        ["05", "Խելացի պացիենտի քարտ", "OPG-ն, վերլուծությունը և վերանայման պատմությունը պահեք մեկ տեղում։"],
        ["06", "Care հետագա վերահսկում", "Սահմանեք խնդրի կամ ատամի հիման վրա հետագա վերահսկման ժամկետը։"],
        ["07", "Պացիենտի հաղորդագրություն", "Ուղարկեք կարգավորված հետագա հաղորդագրությունը և հետևեք առաքման վիճակին։"],
        ["08", "Պացիենտի վերադարձ", "Հետևեք հետագա վերահսկման վիճակին և գործեք պացիենտի վերադարձի ժամանակ։"]
      ]
    },
    plans: {
      kicker: "Երկու կենտրոնացված պլան",
      title: "Ընտրեք միայն վերլուծություն կամ ամբողջական հետագա վերահսկման շղթա։",
      scan: { name: "Teta2 Scan", tagline: "Տեսեք՝ ինչ է թաքնված OPG-ում։", outcome: "Սքան → Հասկանալ → Պահպանել", features: ["Անսահմանափակ OPG վերլուծություն բաժանորդագրության ամսվա ընթացքում", "AI-ով աջակցվող OPG վերլուծություն", "Հնարավոր հայտնաբերումներ", "Ատամ/շրջան ըստ կազմակերպում, որտեղ աջակցվում է", "Տեսողական նշումներ OPG-ի վրա", "AI հաշվետվություն", "Խելացի պացիենտի քարտ", "OPG պատմություն", "Վերլուծությունների պատմություն"] },
      care: { name: "Teta2 Care", tagline: "Մի կորցրեք պացիենտին, որը հետագա վերահսկման կարիք ունի։", outcome: "Սքան → Հասկանալ → Պահպանել → Հետևել → Վերադարձ", features: ["Ամեն ինչ Teta2 Scan-ից", "Խելացի հետագա վերահսկում", "Խնդրի/ատամի հիման վրա ժամկետավորում", "Ավտոմատ պացիենտի հաղորդագրություններ", "Պատասխանների վերահսկում", "Recall կառավարում", "Հետագա վերահսկման վահանակ", "Հայտնաբերման և բուժման հետևման պատմություն", "Պացիենտի վերադարձի վերահսկում"] }
    },
    safety: {
      kicker: "Կլինիկական անվտանգություն ըստ դիզայնի",
      title: "AI-ն աջակցում է բժշկին և չի փոխարինում կլինիկական դատողությանը։",
      body: "Teta2-ը ներկայացնում է AI-ով աջակցվող հնարավոր հայտնաբերումներ մասնագիտական զննման համար։ Վերջնական վերանայումը, ախտորոշումը և բուժման որոշումը մնում են բժշկին։",
      items: [
        ["Մարդը վերահսկման շղթայում", "Յուրաքանչյուր հնարավոր հայտնաբերում հասանելի է բժշկի վերանայման համար։"],
        ["Պաշտպանված կլինիկական տվյալներ", "Մուտքի կառավարումը, գաղտնագրված պահոցը և աուդիտի գրանցումը հարթակի ճարտարապետության մաս են։"],
        ["Պատասխանատու ձևակերպումներ", "Teta2-ը AI արդյունքը չի ներկայացնում որպես վերջնական ախտորոշում և չի հայտարարում չվավերացված ախտորոշիչ ճշտություն։"]
      ]
    },
    pricing: {
      title: "Պարզ գներ՝ կենտրոնացված կլինիկական արժեքի համար։",
      lead: "Երկու պլանն էլ ներառում են անսահմանափակ OPG վերլուծություն բնական կլինիկական օգտագործման համար։ Գործում է Fair Use Policy՝ API չարաշահման կամ աննորմալ զանգվածային ավտոմատ մշակման դեմ։",
      monthly: "ամիս",
      annual: "Տարեկան տարբերակ՝ վճարեք 10 ամսվա համար և ստացեք 12 ամսվա մուտք։",
      market: "Շուկա",
      unlimited: "Անսահմանափակ OPG վերլուծություն",
      choose: "Մուտքի հարցում"
    },
    about: {
      title: "Teta2-ը կառուցված է մեկ կլինիկական շղթայի շուրջ։",
      lead: "Մենք կառուցում ենք կենտրոնացված dental AI՝ OPG ինտելեկտի և պացիենտի հետագա վերահսկման համար, ոչ թե ընդհանուր կլինիկական CRM։ Առևտրային հասանելիության համար օգտագործեք կայքի Teta2 onboarding հոսքը։",
      principle: "Պարզը գերադասելի է համապարփակից։ OPG-ն մնում է կենտրոնում։ Յուրաքանչյուր AI արդյունք պետք է բերի օգտակար կլինիկական գործողության։",
      roadmap: ["Scan՝ հուսալի OPG վերբեռնում, վերլուծություն, հայտնաբերումներ և պացիենտի քարտ", "Care՝ հետագա վերահսկում, հաղորդագրություններ, պատասխաններ և պացիենտի վերադարձ", "Կլինիկական ինտելեկտ՝ ավելի ուժեղ ատամային քարտեզում և երկարաժամկետ համեմատություն՝ վավերացումից հետո", "Growth հավելումներ միայն հիմնական արտադրանքի իրական traction-ից հետո"]
    },
    access: {
      title: "Teta2 մուտքի հարցում",
      lead: "Կլինիկայի onboarding-ը ներկայում իրականացվում է ուղղակի provision-ով։ Հանրային ինքնասպասարկվող գրանցումը դեռ միացված չէ։",
      note: "Առևտրային onboarding-ի ժամանակ ընտրեք Teta2 Scan կամ Teta2 Care։ Մուտքի տվյալներ ստանալու համար կլինիկական workspace-ը նախ պետք է provision արվի։",
      login: "Արդեն provision արված է՞։ Մուտք գործել"
    },
    clinic: {
      dashboard: "Վահանակ", patients: "Պացիենտներ", opg: "OPG վերլուծություն", followups: "Հետագա վերահսկում", messages: "Հաղորդագրություններ", settings: "Կարգավորումներ",
      dashboardTitle: "Կլինիկական գործողությունների վահանակ", dashboardLead: "OPG-ից մինչև հետագա վերահսկում՝ իրական կլինիկական տվյալներով։",
      newPatient: "Նոր պացիենտ", selectPatient: "Ընտրեք պացիենտ", upload: "Վերբեռնել OPG", analyze: "Գործարկել AI-ով աջակցվող վերլուծությունը",
      possibleFinding: "հնարավոր հայտնաբերում", requiresExam: "Պահանջում է ատամնաբույժի զննում",
      noPatient: "Ընտրեք պացիենտ՝ խելացի պացիենտի քարտը բացելու համար։",
      noFollowups: "Ձեր հասանելիության շրջանակում հետագա վերահսկման գրառումներ չկան։",
      messagesLead: "Ընտրված պացիենտի հետագա հաղորդագրությունները կլինիկայի միացված WhatsApp ուղարկող հաշվի միջոցով։",
      careRecord: "Խելացի պացիենտի քարտ", overview: "Ակնարկ", opgHistory: "OPG պատմություն", findings: "Հնարավոր հայտնաբերումներ", timeline: "Հետագա վերահսկում", messageHistory: "Հաղորդագրություններ"
    }
  }
} as const;

export function productCopy(lang: ProductLang) {
  return PRODUCT_COPY[lang];
}
