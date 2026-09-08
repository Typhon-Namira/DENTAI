export type Lang = "en" | "hy";

export const v5Copy = {
  en: {
    brand: { name: "Teta2", tagline: "OPG intelligence and patient follow-up for dental clinics" },
    nav: { product: "Product", how: "How It Works", pricing: "Pricing", safety: "Clinical / Safety", about: "About / Contact", login: "Sign in", access: "Request access" },
    hero: {
      kicker: "AI-powered OPG intelligence + patient follow-up",
      title: "Turn Every OPG Into Actionable Patient Follow-up.",
      lead: "Teta2 helps dental clinics identify possible findings from panoramic X-rays, organize them in a smart patient file, and—through Teta2 Care—follow up with patients automatically.",
      primary: "Analyze an OPG",
      secondary: "See how it works",
      trust1: "AI-assisted analysis",
      trust2: "Dentist examination required",
      trust3: "Private clinic data"
    },
    problem: {
      kicker: "One focused workflow",
      title: "An OPG should not end as a forgotten image.",
      lead: "Teta2 turns the radiograph into a reviewable clinical workflow: possible findings, patient context, follow-up timing and the next patient action.",
      cards: [
        ["Understand faster", "Review AI-generated possible findings by tooth or region where supported."],
        ["Keep the context", "Preserve OPGs, analysis history and clinician review inside the patient's smart record."],
        ["Act on findings", "Teta2 Care turns reviewed clinical context into follow-up tasks and patient messages."]
      ]
    },
    workflow: {
      kicker: "The Teta2 loop",
      title: "Scan → Understand → Record → Follow → Return",
      steps: [
        ["01", "Create patient", "Open a simple smart patient profile with essential clinical and contact context."],
        ["02", "Upload OPG", "Attach the patient's panoramic X-ray to the authorized clinic record."],
        ["03", "AI-assisted analysis", "Teta2 produces possible findings and visual regions for dentist review."],
        ["04", "Clinician review", "Confirm or reject AI findings before they become part of the clinical workflow."],
        ["05", "Smart patient file", "Keep OPGs, analyses, reviewed findings and follow-up history together."],
        ["06", "Follow-up", "Care schedules the next action based on the finding, OPG date and clinic workflow."],
        ["07", "Patient message", "Send configured follow-up communication and track delivery or response."],
        ["08", "Patient return", "The clinic sees the follow-up state and can act when the patient returns."]
      ]
    },
    plans: {
      kicker: "Two plans. One clinical loop.",
      title: "Choose OPG intelligence alone, or connect it to patient return.",
      scan: {
        name: "Teta2 Scan", tagline: "See what's hiding in the OPG.", outcome: "Scan → Understand → Record",
        features: ["Unlimited OPG analysis during the subscription month", "AI-assisted OPG analysis", "Possible findings", "Tooth / region organization where supported", "Visual highlighting", "AI report", "Smart patient profile", "OPG history", "Analysis history"]
      },
      care: {
        name: "Teta2 Care", tagline: "Never lose a patient who needs follow-up.", outcome: "Scan → Understand → Record → Follow → Return",
        features: ["Everything in Teta2 Scan", "Smart follow-up", "Problem / tooth-based follow-up timing", "Automated patient messages", "Patient response tracking", "Recall management", "Follow-up dashboard", "Finding and treatment follow-up history", "Patient-return tracking"]
      }
    },
    pricing: {
      kicker: "Commercial plans", title: "Simple pricing for focused clinical value.",
      lead: "Both plans include unlimited OPG analysis for normal clinical use. Fair Use Policy applies to abnormal automated or bulk processing.",
      monthly: "Monthly", annual: "Annual · 2 months free", armenia: "Armenia", russia: "Russia", perMonth: "/ month", perYear: "/ year", unlimited: "Unlimited OPG analysis", fairUse: "Normal clinical use. Fair Use Policy applies.", chooseScan: "Choose Scan", chooseCare: "Choose Care"
    },
    safety: {
      kicker: "Clinical / Safety", title: "AI supports the dentist. It does not replace clinical judgment.",
      lead: "Teta2 presents AI output as possible findings that require professional examination and clinician review.",
      cards: [
        ["Human in the loop", "Possible findings remain reviewable. The dentist remains responsible for examination, diagnosis and treatment decisions."],
        ["Private clinical data", "The current platform uses authenticated clinic context, tenant-isolated clinical databases, private X-ray storage and audit logging."],
        ["Clear trust UI", "Analysis status, OPG date, AI-generated possible findings and clinician-review state should remain visible in the product."],
        ["Validation before claims", "Teta2 does not present unverified diagnostic-accuracy, regulatory or certification claims in the public interface."]
      ],
      notice: "AI-generated output is assistive clinical information. Possible findings require professional examination."
    },
    about: {
      kicker: "About Teta2", title: "A focused dental AI product, not another all-in-one clinic CRM.",
      lead: "Teta2 is built around one measurable workflow: turn an OPG into reviewable clinical context, preserve that context, and help the clinic follow up with the patient.",
      principles: [["Simple beats comprehensive", "Features must reinforce the OPG → follow-up workflow."], ["OPG is the center", "The radiograph and its reviewed findings remain the primary clinical surface."], ["Findings must lead to action", "AI output should connect to a useful clinical workflow."], ["Care must create return value", "Follow-up is designed to help clinics act on patients who otherwise disappear after an OPG."]]
    },
    auth: {
      loginTitle: "Sign in to your clinic", loginLead: "Use the clinic slug and credentials provisioned for your clinic.", slug: "Clinic slug", identifier: "Email or username", password: "Password", submit: "Sign in securely", submitting: "Signing in…", back: "Back to Teta2",
      requestTitle: "Request Teta2 access", requestLead: "Public self-service provisioning is not exposed by the current backend. Clinic activation is handled through the Teta2 onboarding process.", existing: "Already activated? Sign in", plan: "Plan", market: "Market", activation: "Clinic activation", activationCopy: "Choose the commercial plan you want to evaluate. A clinic account must still be provisioned before login credentials can be issued."
    },
    app: {
      nav: { dashboard: "Dashboard", patients: "Patients", analysis: "OPG Analysis", followups: "Follow-ups", messages: "Messages", settings: "Settings" },
      greeting: "Clinical workspace", subtitle: "OPG intelligence, patient records and follow-up in one focused workflow.",
      dashboardTitle: "Clinic overview", dashboardLead: "Real activity from the authenticated clinic context.",
      metrics: { patients: "Patients", analyses: "OPG analyses", followups: "Follow-ups", due: "Due follow-ups", branches: "Branches", doctors: "Doctors" },
      patientTitle: "Smart Patient Files", patientLead: "Essential patient context, OPG history, possible findings and follow-up status.", addPatient: "Add patient", patientNumber: "Patient number", firstName: "First name", lastName: "Last name", branch: "Branch", create: "Create patient", cancel: "Cancel",
      opgTitle: "OPG Analysis", opgLead: "Upload a panoramic X-ray, run AI-assisted analysis and review possible findings before clinical use.", selectPatient: "Select patient", selectOpg: "Select OPG", upload: "Upload OPG", run: "Run AI-assisted analysis", processing: "Processing…", noPatient: "Choose a patient to start an OPG workflow.", noOpg: "No OPG uploaded for this patient yet.",
      followTitle: "Follow-ups", followLead: "Turn reviewed clinical context into the next patient action.", all: "All", scheduled: "Scheduled", dueStatus: "Due", completed: "Completed", cancelled: "Cancelled", markCompleted: "Mark completed", noFollowups: "No follow-ups match this view.",
      messagesTitle: "Messages", messagesLead: "Connect clinic WhatsApp and manage patient follow-up communication from the same patient context.", choosePatientMessage: "Choose a patient to manage follow-up messaging.",
      settingsTitle: "Clinic settings", settingsLead: "Authenticated clinic context and access information.", role: "Role", clinicId: "Clinic ID", branchScope: "Branch scope", backend: "Backend", ready: "Ready", unavailable: "Unavailable", clinicianNotice: "Possible findings require dentist examination and clinician review."
    }
  },
  hy: {
    brand: { name: "Teta2", tagline: "OPG ինտելեկտ և պացիենտների հետագա վերահսկում ատամնաբուժական կլինիկաների համար" },
    nav: { product: "Ապրանք", how: "Ինչպես է աշխատում", pricing: "Գներ", safety: "Կլինիկական անվտանգություն", about: "Մեր մասին / Կապ", login: "Մուտք", access: "Դիմել հասանելիության համար" },
    hero: {
      kicker: "AI-ով աշխատող OPG ինտելեկտ + պացիենտների հետագա վերահսկում",
      title: "Յուրաքանչյուր OPG-ն վերածեք գործնական պացիենտի հետագա վերահսկման։",
      lead: "Teta2-ը օգնում է ատամնաբուժական կլինիկաներին համայնապատկերային ռենտգեններում տեսնել հնարավոր հայտնաբերումները, կազմակերպել դրանք խելացի պացիենտի քարտում և Teta2 Care-ի միջոցով ավտոմատ շարունակել պացիենտի հետ կապը։",
      primary: "Վերլուծել OPG", secondary: "Տեսնել ինչպես է աշխատում", trust1: "AI-ով աջակցվող վերլուծություն", trust2: "Պահանջվում է ատամնաբույժի զննում", trust3: "Կլինիկայի մասնավոր տվյալներ"
    },
    problem: {
      kicker: "Մեկ կենտրոնացած աշխատանքային հոսք", title: "OPG-ն չպետք է ավարտվի որպես մոռացված պատկեր։",
      lead: "Teta2-ը ռենտգենը վերածում է վերանայվող կլինիկական հոսքի՝ հնարավոր հայտնաբերումներ, պացիենտի համատեքստ, հետագա վերահսկման ժամկետ և հաջորդ գործողություն։",
      cards: [["Ավելի արագ հասկանալ", "Վերանայեք AI-ի ստեղծած հնարավոր հայտնաբերումները ըստ ատամի կամ շրջանի, երբ դա աջակցվում է։"], ["Պահպանել համատեքստը", "OPG-ները, վերլուծությունների պատմությունը և բժշկի վերանայումը պահեք պացիենտի խելացի քարտում։"], ["Գործել հայտնաբերումների հիման վրա", "Teta2 Care-ը վերանայված կլինիկական համատեքստը վերածում է հետագա վերահսկման առաջադրանքների և պացիենտի հաղորդագրությունների։"]]
    },
    workflow: {
      kicker: "Teta2-ի հիմնական հոսքը", title: "Սքանավորում → Հասկանալ → Գրանցել → Հետևել → Վերադարձ",
      steps: [["01", "Ստեղծել պացիենտ", "Բացեք պարզ խելացի պացիենտի քարտ՝ անհրաժեշտ կլինիկական և կոնտակտային տվյալներով։"], ["02", "Վերբեռնել OPG", "Կցեք պացիենտի համայնապատկերային ռենտգենը թույլատրված կլինիկական քարտին։"], ["03", "AI-ով աջակցվող վերլուծություն", "Teta2-ը ստեղծում է հնարավոր հայտնաբերումներ և տեսողական շրջաններ՝ բժշկի վերանայման համար։"], ["04", "Բժշկի վերանայում", "Հաստատեք կամ մերժեք AI հայտնաբերումները մինչև դրանք կլինիկական հոսքում օգտագործելը։"], ["05", "Խելացի պացիենտի քարտ", "OPG-ները, վերլուծությունները, վերանայված հայտնաբերումները և հետագա վերահսկման պատմությունը պահեք միասին։"], ["06", "Հետագա վերահսկում", "Care-ը պլանավորում է հաջորդ գործողությունը՝ ըստ հայտնաբերման, OPG-ի ամսաթվի և կլինիկայի հոսքի։"], ["07", "Պացիենտի հաղորդագրություն", "Ուղարկեք կարգավորված հիշեցումը և հետևեք առաքման կամ պատասխանի վիճակին։"], ["08", "Պացիենտի վերադարձ", "Կլինիկան տեսնում է հետագա վերահսկման վիճակը և գործում է պացիենտի վերադարձի ժամանակ։"]
    },
    plans: {
      kicker: "Երկու պլան. մեկ կլինիկական հոսք։", title: "Ընտրեք միայն OPG ինտելեկտը կամ միացրեք այն պացիենտի վերադարձի հոսքին։",
      scan: { name: "Teta2 Scan", tagline: "Տեսեք, թե ինչ է թաքնված OPG-ում։", outcome: "Սքանավորում → Հասկանալ → Գրանցել", features: ["Անսահմանափակ OPG վերլուծություն բաժանորդագրության ամսվա ընթացքում", "AI-ով աջակցվող OPG վերլուծություն", "Հնարավոր հայտնաբերումներ", "Ատամի / շրջանի կազմակերպում, երբ աջակցվում է", "Տեսողական ընդգծում", "AI հաշվետվություն", "Խելացի պացիենտի քարտ", "OPG պատմություն", "Վերլուծությունների պատմություն"] },
      care: { name: "Teta2 Care", tagline: "Մի կորցրեք պացիենտին, ով հետագա վերահսկման կարիք ունի։", outcome: "Սքանավորում → Հասկանալ → Գրանցել → Հետևել → Վերադարձ", features: ["Ամեն ինչ Teta2 Scan-ից", "Խելացի հետագա վերահսկում", "Խնդրի / ատամի հիմքով ժամկետավորում", "Ավտոմատ պացիենտի հաղորդագրություններ", "Պացիենտի պատասխանի հետևում", "Հիշեցումների կառավարում", "Հետագա վերահսկման վահանակ", "Հայտնաբերման և բուժման հետևման պատմություն", "Պացիենտի վերադարձի հետևում"] }
    },
    pricing: {
      kicker: "Առևտրային պլաններ", title: "Պարզ գներ՝ կենտրոնացած կլինիկական արժեքի համար։", lead: "Երկու պլաններն էլ ներառում են անսահմանափակ OPG վերլուծություն սովորական կլինիկական օգտագործման համար։ Fair Use Policy-ը կիրառվում է անսովոր ավտոմատ կամ զանգվածային մշակման դեպքում։", monthly: "Ամսական", annual: "Տարեկան · 2 ամիս անվճար", armenia: "Հայաստան", russia: "Ռուսաստան", perMonth: "/ ամիս", perYear: "/ տարի", unlimited: "Անսահմանափակ OPG վերլուծություն", fairUse: "Սովորական կլինիկական օգտագործում։ Գործում է Fair Use Policy։", chooseScan: "Ընտրել Scan", chooseCare: "Ընտրել Care"
    },
    safety: {
      kicker: "Կլինիկական անվտանգություն", title: "AI-ը աջակցում է բժշկին, բայց չի փոխարինում կլինիկական դատողությանը։", lead: "Teta2-ը AI-ի արդյունքները ներկայացնում է որպես հնարավոր հայտնաբերումներ, որոնք պահանջում են մասնագիտական զննում և բժշկի վերանայում։", cards: [["Բժիշկը մնում է որոշում կայացնողը", "Հնարավոր հայտնաբերումները մնում են վերանայվող։ Զննումը, ախտորոշումը և բուժման որոշումները բժշկի պատասխանատվությունն են։"], ["Մասնավոր կլինիկական տվյալներ", "Ներկա հարթակը օգտագործում է նույնականացված կլինիկայի համատեքստ, մեկուսացված կլինիկական տվյալների բազաներ, մասնավոր X-ray պահոց և audit logging։"], ["Հստակ վստահության UI", "Վերլուծության վիճակը, OPG ամսաթիվը, AI-ի հնարավոր հայտնաբերումները և բժշկի վերանայման վիճակը պետք է տեսանելի մնան։"], ["Վալիդացիա՝ մինչև պնդումներ", "Teta2-ը հանրային միջերեսում չի ներկայացնում չհաստատված ճշգրտության, կարգավորիչ կամ հավաստագրման պնդումներ։"]], notice: "AI-ի ստեղծած արդյունքները օժանդակ կլինիկական տեղեկատվություն են։ Հնարավոր հայտնաբերումները պահանջում են մասնագիտական զննում։"
    },
    about: {
      kicker: "Teta2-ի մասին", title: "Կենտրոնացած dental AI ապրանք, ոչ թե հերթական all-in-one CRM։", lead: "Teta2-ը կառուցված է մեկ չափելի հոսքի շուրջ՝ OPG-ն վերածել վերանայվող կլինիկական համատեքստի, պահպանել այն և օգնել կլինիկային շարունակել կապը պացիենտի հետ։", principles: [["Պարզը գերազանցում է համապարփակին", "Յուրաքանչյուր ֆունկցիա պետք է ուժեղացնի OPG → հետագա վերահսկում հոսքը։"], ["OPG-ն կենտրոնում է", "Ռենտգենը և դրա վերանայված հայտնաբերումները մնում են հիմնական կլինիկական մակերեսը։"], ["Հայտնաբերումը պետք է հանգեցնի գործողության", "AI-ի արդյունքը պետք է միանա օգտակար կլինիկական հոսքին։"], ["Care-ը պետք է վերադարձի արժեք ստեղծի", "Հետագա վերահսկումը օգնում է կլինիկային գործել այն պացիենտների դեպքում, որոնք հակառակ դեպքում կարող էին անհետանալ OPG-ից հետո։"]]
    },
    auth: {
      loginTitle: "Մուտք կլինիկա", loginLead: "Օգտագործեք ձեր կլինիկայի համար տրամադրված slug-ը և մուտքի տվյալները։", slug: "Կլինիկայի slug", identifier: "Էլ․ հասցե կամ օգտանուն", password: "Գաղտնաբառ", submit: "Անվտանգ մուտք", submitting: "Մուտք…", back: "Վերադառնալ Teta2", requestTitle: "Դիմել Teta2 հասանելիության համար", requestLead: "Ներկա backend-ը դեռ չի տրամադրում հանրային ինքնասպասարկման provisioning endpoint։ Կլինիկայի ակտիվացումը կատարվում է Teta2 onboarding գործընթացով։", existing: "Արդեն ակտիվացված է՞։ Մուտք գործել", plan: "Պլան", market: "Շուկա", activation: "Կլինիկայի ակտիվացում", activationCopy: "Ընտրեք այն առևտրային պլանը, որը ցանկանում եք գնահատել։ Մուտքի տվյալներ ստանալու համար կլինիկայի հաշիվը դեռ պետք է provision արվի։"
    },
    app: {
      nav: { dashboard: "Վահանակ", patients: "Պացիենտներ", analysis: "OPG վերլուծություն", followups: "Հետագա վերահսկում", messages: "Հաղորդագրություններ", settings: "Կարգավորումներ" },
      greeting: "Կլինիկական աշխատանքային տարածք", subtitle: "OPG ինտելեկտ, պացիենտի քարտեր և հետագա վերահսկում՝ մեկ կենտրոնացած հոսքում։", dashboardTitle: "Կլինիկայի ակնարկ", dashboardLead: "Իրական ակտիվություն նույնականացված կլինիկական համատեքստից։", metrics: { patients: "Պացիենտներ", analyses: "OPG վերլուծություններ", followups: "Հետագա վերահսկումներ", due: "Ժամկետանց / հասած", branches: "Մասնաճյուղեր", doctors: "Բժիշկներ" },
      patientTitle: "Խելացի պացիենտի քարտեր", patientLead: "Պացիենտի հիմնական տվյալներ, OPG պատմություն, հնարավոր հայտնաբերումներ և հետագա վերահսկման վիճակ։", addPatient: "Ավելացնել պացիենտ", patientNumber: "Պացիենտի համար", firstName: "Անուն", lastName: "Ազգանուն", branch: "Մասնաճյուղ", create: "Ստեղծել պացիենտ", cancel: "Չեղարկել",
      opgTitle: "OPG վերլուծություն", opgLead: "Վերբեռնեք համայնապատկերային ռենտգենը, գործարկեք AI-ով աջակցվող վերլուծությունը և կլինիկական օգտագործումից առաջ վերանայեք հնարավոր հայտնաբերումները։", selectPatient: "Ընտրել պացիենտ", selectOpg: "Ընտրել OPG", upload: "Վերբեռնել OPG", run: "Գործարկել AI-ով աջակցվող վերլուծությունը", processing: "Մշակվում է…", noPatient: "OPG հոսքը սկսելու համար ընտրեք պացիենտ։", noOpg: "Այս պացիենտի համար դեռ OPG չկա։",
      followTitle: "Հետագա վերահսկում", followLead: "Վերանայված կլինիկական համատեքստը վերածեք հաջորդ պացիենտի գործողության։", all: "Բոլորը", scheduled: "Պլանավորված", dueStatus: "Ժամկետը հասել է", completed: "Ավարտված", cancelled: "Չեղարկված", markCompleted: "Նշել ավարտված", noFollowups: "Այս տեսքի համար հետագա վերահսկումներ չկան։",
      messagesTitle: "Հաղորդագրություններ", messagesLead: "Միացրեք կլինիկայի WhatsApp-ը և կառավարեք պացիենտի հետագա հաղորդակցությունը նույն համատեքստից։", choosePatientMessage: "Ընտրեք պացիենտ՝ հետագա հաղորդագրությունները կառավարելու համար։", settingsTitle: "Կլինիկայի կարգավորումներ", settingsLead: "Նույնականացված կլինիկայի համատեքստ և հասանելիության տեղեկատվություն։", role: "Դեր", clinicId: "Կլինիկայի ID", branchScope: "Մասնաճյուղերի հասանելիություն", backend: "Backend", ready: "Պատրաստ", unavailable: "Անհասանելի", clinicianNotice: "Հնարավոր հայտնաբերումները պահանջում են ատամնաբույժի զննում և բժշկի վերանայում։"
    }
  }
} as const;

export function c(lang: Lang) { return v5Copy[lang]; }
