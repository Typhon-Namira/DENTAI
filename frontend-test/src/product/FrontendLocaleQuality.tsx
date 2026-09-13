import { useEffect } from "react";

type Lang = "en" | "hy" | "ru";

type TextMap = Record<string, string>;

const EN: TextMap = {
  "Care API is not deployed on the connected backend yet.": "Follow-up services are not available on the connected server yet.",
  "Active care plans": "Active follow-up plans",
  "Active AI conversations": "Active patient conversations",
  "Live WhatsApp conversations handled by Teta2 after your clinical approval.": "WhatsApp follow-up conversations handled by Teta2 after your clinical approval.",
  "Patient-accepted check-up times stay here until you approve them.": "Check-up times selected by patients stay here until you approve them.",
  "Request another time": "Suggest another time",
  "Care backend is not on the same release as this frontend. Generation is temporarily unavailable until the protected backend deployment completes.": "Follow-up plan generation is temporarily unavailable while the protected backend finishes updating.",
  "Followup Ready": "Follow-up ready",
  "Waiting Previous Tooth": "Waiting for previous tooth",
  "Attended Not Treated": "Attended — not treated",
  "No Show": "No-show",
};

const HY: TextMap = {
  /* Dashboard shell */
  "Վահանակ": "Գլխավոր վահանակ",
  "Հետագա պլաններ": "Հետագա վերահսկման պլաններ",
  "AI զրույցներ": "Պացիենտների հետ զրույցներ",
  "Teta2 · կլինիկական follow-up workspace": "Teta2 · կլինիկական հետագա վերահսկման միջավայր",
  "Սպասում է ձեր հաստատմանը": "Սպասում են ձեր հաստատմանը",
  "Ակտիվ care պլաններ": "Ակտիվ հետագա վերահսկման պլաններ",
  "Ակտիվ AI զրույցներ": "Ակտիվ զրույցներ պացիենտների հետ",
  "Ժամկետը հասած follow-up": "Ժամկետը հասած հետագա վերահսկումներ",
  "Care API-ն դեռ տեղադրված չէ միացված backend-ում։": "Հետագա վերահսկման ծառայությունն այս պահին հասանելի չէ միացված սերվերում։",
  "Ընտրեք պացիենտ՝ բժշկական քարտը բացելու համար։": "Ընտրեք պացիենտ՝ նրա կլինիկական քարտը բացելու համար։",
  "Գործարկել AI": "Գործարկել AI վերլուծությունը",
  "Վերանայեք և փոխեք ատամային follow-up պլանը մինչև outreach-ի հաստատումը։": "Վերանայեք և անհրաժեշտության դեպքում փոփոխեք յուրաքանչյուր ատամի հետագա վերահսկման պլանը՝ նախքան պացիենտի հետ կապը սկսելը։",
  "Հաստատել պլանը և սկսել outreach": "Հաստատել պլանը և սկսել կապը պացիենտի հետ",
  "WhatsApp-ի կենդանի զրույցները՝ ձեր կլինիկական հաստատումից հետո։": "WhatsApp-ի հետագա վերահսկման զրույցները սկսվում են ձեր կլինիկական հաստատումից հետո։",
  "Պացիենտի ընդունած ժամերը մնում են այստեղ մինչև ձեր հաստատումը։": "Պացիենտի ընտրած ստուգման ժամերը կմնան այստեղ մինչև ձեր հաստատումը։",
  "Teta2-ը այս կանոններով է պացիենտին առաջարկում ազատ ժամեր։": "Teta2-ը պացիենտներին հասանելի ժամեր է առաջարկում այս կանոնների հիման վրա։",

  /* OPG + AI */
  "No analysis selected": "Վերլուծություն ընտրված չէ",
  "Select an X-ray and run DENTAI V5.": "Ընտրեք ռենտգեն պատկերը և գործարկեք DENTAI V5-ը։",
  "Review saved.": "Վերանայումը պահպանվել է։",
  "Analysis failed": "Վերլուծությունը ձախողվել է",
  "Interactive OPG": "Ինտերակտիվ OPG",
  "DENTAI clinical findings on the radiograph": "DENTAI-ի կլինիկական արդյունքները ռենտգեն պատկերի վրա",
  "Green = treated or restored teeth · red = pathological findings · red intensity reflects model confidence.": "Կանաչը՝ բուժված կամ վերականգնված ատամներ · կարմիրը՝ հնարավոր պաթոլոգիական փոփոխություններ · կարմիրի ուժգնությունը ցույց է տալիս մոդելի վստահության միավորը։",
  "AI report": "AI զեկույց",
  "AI overlay": "AI շերտ",
  "All": "Բոլորը",
  "Pending": "Սպասում է վերանայման",
  "Confirmed": "Հաստատված",
  "Rejected": "Մերժված",
  "The X-ray for this analysis is not available.": "Այս վերլուծության ռենտգեն պատկերը հասանելի չէ։",
  "Loading radiograph…": "Բեռնվում է ռենտգեն պատկերը…",
  "The radiograph could not be loaded.": "Չհաջողվեց բեռնել ռենտգեն պատկերը։",
  "AI clinical report": "AI կլինիկական զեկույց",
  "Key observation": "Հիմնական դիտարկում",
  "Monitoring": "Հետագա վերահսկում",
  "For the clinician": "Բժշկի ուշադրությանը",
  "AI summary does not replace clinician assessment.": "AI ամփոփումը չի փոխարինում բժշկի կլինիկական գնահատմանը։",
  "Finding review filters": "Արդյունքների վերանայման զտիչներ",
  "DENTAI clinical finding overlay": "DENTAI-ի կլինիկական արդյունքների շերտ",
  "This is an AI-assisted observation and is not a final diagnosis until reviewed by the clinician.": "Սա AI-աջակցվող դիտարկում է և վերջնական ախտորոշում չէ․ այն պետք է վերանայի բժիշկը։",

  /* Follow-up generation */
  "AI FOLLOW-UP ORCHESTRATION": "AI ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՄԱՆ ԿԱՌԱՎԱՐՈՒՄ",
  "Waiting for analysis to complete": "Սպասում ենք վերլուծության ավարտին",
  "The Generate button will unlock automatically as soon as the current OPG analysis finishes. No page refresh is required.": "«Ստեղծել AI-ով» կոճակը կակտիվանա ավտոմատ, երբ ընթացիկ OPG վերլուծությունն ավարտվի։ Էջը թարմացնելու կարիք չկա։",
  "Generate with AI": "Ստեղծել AI-ով",
  "Follow-up plan ready": "Հետագա վերահսկման պլանը պատրաստ է",
  "Generate follow-up plan": "Ստեղծել հետագա վերահսկման պլան",
  "No pathological tooth findings with a resolved FDI are available in this completed OPG analysis.": "Այս ավարտված OPG վերլուծության մեջ FDI համարով նույնականացված՝ պլանում ընդգրկելու ենթակա պաթոլոգիական փոփոխություն չկա։",
  "Checking pathological tooth eligibility with the care backend…": "Ստուգվում է՝ որ ատամները կարող են ընդգրկվել հետագա վերահսկման պլանում…",
  "Open follow-up plans": "Բացել հետագա վերահսկման պլանները",
  "Generating…": "Ստեղծվում է…",
  "Clinician review is recommended; doctor remains in control.": "Խորհուրդ է տրվում բժշկի վերանայում․ վերջնական վերահսկողությունը մնում է բժշկին։",
  "Doctor remains in control": "Վերջնական վերահսկողությունը մնում է բժշկին",
  "Recommended: review AI findings before approving outreach, but generation is available now.": "Խորհուրդ է տրվում AI արդյունքները վերանայել՝ նախքան պացիենտի հետ կապը հաստատելը, սակայն պլանը կարելի է ստեղծել արդեն հիմա։",
  "No eligible pathological/red tooth findings are available in this completed OPG analysis.": "Այս ավարտված OPG վերլուծության մեջ պլանում ընդգրկելու ենթակա պաթոլոգիական փոփոխություն չկա։",

  /* Follow-up workspace */
  "CLINIC FOLLOW-UP QUEUE": "ԿԼԻՆԻԿԱՅԻ ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՄԱՆ ՀԵՐԹ",
  "Patient follow-up plans": "Պացիենտների հետագա վերահսկման պլաններ",
  "One clinic WhatsApp connection serves all patients. Each patient keeps their own stored WhatsApp number and sequential tooth plan.": "Կլինիկայի մեկ WhatsApp կապն օգտագործվում է բոլոր պացիենտների համար։ Յուրաքանչյուր պացիենտի WhatsApp համարը և ատամների հերթական պլանը պահվում են առանձին։",
  "patient plans": "պացիենտի պլան",
  "Search patient, ID or WhatsApp": "Փնտրել պացիենտ, համար կամ WhatsApp",
  "Showing up to 200 recent plans": "Ցուցադրվում են մինչև 200 վերջին պլանները",
  "No matching follow-up plans.": "Համապատասխան հետագա վերահսկման պլան չի գտնվել։",
  "Patient": "Պացիենտ",
  "Not registered": "Գրանցված չէ",
  "Approve sequential outreach": "Հաստատել հերթական կապը պացիենտի հետ",
  "Activating…": "Ակտիվացվում է…",
  "Priority": "Առաջնահերթություն",
  "AI finding": "AI արդյունք",
  "Conversation start:": "Զրույցի մեկնարկ՝",
  "After previous tooth outcome": "Նախորդ ատամի վերջնական արդյունքից հետո",
  "Outcome:": "Արդյունք՝",
  "Clinical follow-up target": "Կլինիկական վերահսկման նպատակային ժամկետ",
  "Recommended window": "Առաջարկվող ժամանակահատված",
  "Rationale": "Հիմնավորում",
  "WhatsApp opening message": "WhatsApp-ի առաջին հաղորդագրություն",
  "Saving…": "Պահպանվում է…",
  "Save tooth plan": "Պահպանել ատամի պլանը",
  "CLINIC WHATSAPP": "ԿԼԻՆԻԿԱՅԻ WHATSAPP",
  "Clinic WhatsApp connected": "Կլինիկայի WhatsApp-ը միացված է",
  "Connect clinic WhatsApp": "Միացնել կլինիկայի WhatsApp-ը",
  "Connected": "Միացված է",
  "Disconnected": "Անջատված է",
  "Disconnect": "Անջատել",
  "Connect with QR": "Միացնել QR կոդով",
  "WHATSAPP LINKED DEVICE": "WHATSAPP-Ի ԿԱՊՎԱԾ ՍԱՐՔ",
  "Scan with the clinic phone": "Սկանավորեք կլինիկայի հեռախոսով",
  "Generating secure QR…": "Ստեղծվում է անվտանգ QR կոդ…",
  "WhatsApp → Linked devices → Link a device → scan this code.": "WhatsApp → Կապված սարքեր → Կապել սարք → սկանավորեք այս կոդը։",
  "LIVE AI CONVERSATION": "AI-ԱՋԱԿՑՎՈՂ ԱԿՏԻՎ ԶՐՈՒՅՑ",
  "Patient conversation": "Զրույց պացիենտի հետ",
  "Every WhatsApp message is mirrored here.": "WhatsApp-ի յուրաքանչյուր հաղորդագրություն արտացոլվում է այստեղ։",
  "Live sync · 5s": "Ուղիղ համաժամացում · 5 վրկ",
  "APPOINTMENT AWAITING DOCTOR APPROVAL": "ԱՅՑԸ ՍՊԱՍՈՒՄ Է ԲԺՇԿԻ ՀԱՍՏԱՏՄԱՆԸ",
  "CONVERSATION APPOINTMENT": "ԶՐՈՒՅՑԻՆ ԿԱՊՎԱԾ ԱՅՑ",
  "Teta2 AI": "Teta2 AI",
  "No messages for this patient yet.": "Այս պացիենտի համար դեռ հաղորդագրություն չկա։",
  "VISIT OUTCOME → AI FOLLOW-UP": "ԱՅՑԻ ԱՐԴՅՈՒՆՔ → AI ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՈՒՄ",
  "Appointment outcomes": "Այցերի վերջնական արդյունքներ",
  "Record what actually happened. Teta2 uses the outcome to continue the current tooth or unlock the next priority tooth.": "Գրանցեք այցի իրական արդյունքը։ Teta2-ն այն օգտագործում է ընթացիկ ատամի փուլը շարունակելու կամ հաջորդ առաջնահերթ ատամը ակտիվացնելու համար։",
  "Optional clinical note": "Կլինիկական նշում (ըստ ցանկության)",
  "Came · treated": "Այցելել է · բուժվել է",
  "Came · not treated": "Այցելել է · բուժում չի կատարվել",
  "No-show": "Չի ներկայացել",

  /* Case workspace */
  "Not scheduled": "Պլանավորված չէ",
  "Follow-up activated. The first outreach is scheduled; later teeth stay locked to the sequence.": "Հետագա վերահսկումն ակտիվացված է։ Առաջին կապը պլանավորված է, իսկ հաջորդ ատամները կմնան հերթականությամբ փակ՝ մինչև նախորդ փուլի ավարտը։",
  "FOLLOW-UP CASES": "ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՄԱՆ ԳՈՐԾԵՐ",
  "Patient follow-up workspace": "Պացիենտների հետագա վերահսկման միջավայր",
  "One patient = one organized case file. All dates are shown in the clinic timezone.": "Յուրաքանչյուր պացիենտ ունի առանձին կազմակերպված գործ։ Բոլոր ամսաթվերը ցուցադրվում են կլինիկայի ժամային գոտով։",
  "Clinic timezone": "Կլինիկայի ժամային գոտի",
  "No matching patient cases.": "Համապատասխան պացիենտի գործ չի գտնվել։",
  "No follow-up case selected.": "Հետագա վերահսկման գործ ընտրված չէ։",
  "Clinic WhatsApp": "Կլինիկայի WhatsApp",
  "QR connect": "Միացնել QR-ով",
  "Connect clinic WhatsApp": "Միացնել կլինիկայի WhatsApp-ը",
  "Close QR": "Փակել QR պատուհանը",
  "Scan QR to connect": "Սկանավորեք QR կոդը՝ միացնելու համար",
  "Generating QR…": "Ստեղծվում է QR կոդ…",
  "PATIENT FOLLOW-UP FILE": "ՊԱՑԻԵՆՏԻ ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՄԱՆ ԳՈՐԾ",
  "WhatsApp not registered": "WhatsApp համարը գրանցված չէ",
  "Approve outreach": "Հաստատել կապը պացիենտի հետ",
  "Teeth in plan": "Պլանում ընդգրկված ատամներ",
  "Current tooth": "Ընթացիկ ատամ",
  "First outreach": "Առաջին կապ",
  "Timezone": "Ժամային գոտի",
  "FIRST WHATSAPP OUTREACH": "WHATSAPP-Ի ԱՌԱՋԻՆ ՀԱՂՈՐԴԱԳՐՈՒԹՅՈՒՆ",
  "Doctor can change this before the first message is sent": "Բժիշկը կարող է փոխել ժամը մինչև առաջին հաղորդագրության ուղարկումը",
  "Scheduled outreach": "Պլանավորված կապ",
  "This controls when the AI sends the opening WhatsApp message for the first priority tooth.": "Այստեղ սահմանվում է, թե երբ AI-ը կուղարկի WhatsApp-ի առաջին հաղորդագրությունը առաջին առաջնահերթ ատամի համար։",
  "Save send time": "Պահպանել ուղարկման ժամը",
  "TREATMENT FOLLOW-UP SEQUENCE": "ԲՈՒԺՄԱՆ ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՄԱՆ ՀԵՐԹԱԿԱՆՈՒԹՅՈՒՆ",
  "Tooth-by-tooth plan": "Պլան՝ ատամ առ ատամ",
  "Later teeth unlock only after the previous outcome.": "Հաջորդ ատամներն ակտիվանում են միայն նախորդ փուլի վերջնական արդյունքից հետո։",
  "Clinical follow-up": "Կլինիկական հետագա վերահսկում",
  "Opening message will be prepared before outreach.": "Առաջին հաղորդագրությունը կպատրաստվի կապը սկսելուց առաջ։",

  /* Booking */
  "Loading live availability…": "Բեռնվում են հասանելի ժամերը…",
  "Booking link unavailable": "Ամրագրման հղումը հասանելի չէ։",
  "Could not request appointment": "Չհաջողվեց ուղարկել այցի հարցումը։",

  /* Public chrome/login */
  "Cookie-ներ և browser storage": "Քուքիներ և դիտարկչի պահոց",
  "Կլինիկական AI-ի սահմանափակումներ": "Կլինիկական AI-ի պատասխանատվության սահմանափակում",
  "Միայն անհրաժեշտ browser storage": "Միայն անհրաժեշտ դիտարկչային պահոց",
  "Teta2-ը չի օգտագործում գովազդային կամ analytics cookie-ներ։ Լեզուն պահվում է այս սարքում, իսկ մուտքի տվյալները՝ միայն browser session-ի ընթացքում։": "Teta2-ը չի օգտագործում գովազդային կամ վերլուծական քուքիներ։ Ընտրված լեզուն պահվում է այս սարքում, իսկ մուտքի տվյալները՝ միայն դիտարկչի ընթացիկ աշխատաշրջանի ընթացքում։",
  "Օգտագործեք ձեր provision արված clinic slug-ը և հաշիվը։": "Օգտագործեք ձեր կլինիկայի ակտիվացման ժամանակ տրամադրված նույնականացուցիչն ու հաշիվը։",
  "Clinic slug": "Կլինիկայի նույնականացուցիչ",
  "SECURE CLINIC ACCESS": "ԱՆՎՏԱՆԳ ՄՈՒՏՔ ԿԼԻՆԻԿԱՅԻ ՀԱՄԱՐ",
  "Clinician-controlled · Patient-specific · Follow-up visible": "Բժիշկը վերահսկում է · Անհատական պացիենտի համար · Հետագա վերահսկումը տեսանելի է",

  /* Access request */
  "Ուղարկեք մեկ անվտանգ հայտ։ Հայտում նշված երկիրը review-ի պահին ավտոմատ ընտրում է ճիշտ market pricing-ը։": "Ուղարկեք մեկ անվտանգ հայտ։ Հայտում նշված երկիրը ստուգման ընթացքում ավտոմատ որոշում է համապատասխան շուկան և գինը։",
  "Funding Plan": "Մեկնարկային արտոնյալ սակագին",
  "առաջին 50 clinics": "առաջին 50 կլինիկաների համար",
  "Standard": "Ստանդարտ",
  "մեկ clinic / ամիս": "մեկ կլինիկայի համար / ամիս",
  "Clinical workspace-ը շարունակական է": "Կլինիկայի աշխատանքային միջավայրը պահպանվում է",
  "Access-ի ավարտից հետո workspace-ը կողպվում է, ոչ թե ջնջվում։ Renewal-ը վերադարձնում է նույն clinic data-ն և history-ն։": "Մուտքի ժամկետի ավարտից հետո աշխատանքային միջավայրը կողպվում է, ոչ թե ջնջվում։ Երկարաձգումը վերականգնում է նույն տվյալներն ու պատմությունը։",
  "Request submitted": "Հայտն ուղարկված է",
  "Your application is waiting for review. If approved, Teta2 will automatically select the Armenia or Russia pricing email from the country in your request.": "Ձեր հայտը սպասում է ստուգման։ Հաստատվելու դեպքում Teta2-ը հայտում նշված երկրի հիման վրա կկիրառի Հայաստանի կամ Ռուսաստանի համապատասխան գինը։",
  "Back to Teta2": "Վերադառնալ Teta2",
  "Clinic name *": "Կլինիկայի անվանում *",
  "Country *": "Երկիր *",
  "Select market": "Ընտրեք շուկան",
  "Armenia": "Հայաստան",
  "Russia": "Ռուսաստան",
  "City *": "Քաղաք *",
  "Pricing selected from country": "Գինը որոշվում է ըստ երկրի",
  "Clinic address": "Կլինիկայի հասցե",
  "Website": "Կայք",
  "Contact person *": "Կոնտակտային անձ *",
  "Role / title *": "Պաշտոն / դեր *",
  "Director, owner, dentist…": "Տնօրեն, սեփականատեր, ատամնաբույժ…",
  "Email *": "Էլ․ փոստ *",
  "Phone *": "Հեռախոս *",
  "Number of dentists *": "Ատամնաբույժների քանակ *",
  "Number of branches *": "Մասնաճյուղերի քանակ *",
  "Anything we should know?": "Կա՞ որևէ լրացուցիչ տեղեկություն, որ պետք է իմանանք։",
  "Funding Plan availability is confirmed during review. Submission does not reserve a slot or activate access.": "Մեկնարկային արտոնյալ սակագնի հասանելիությունը հաստատվում է հայտի ստուգման ժամանակ։ Հայտ ուղարկելը տեղ չի ամրագրում և մուտքը չի ակտիվացնում։",
  "AI-ով OPG ինտելեկտ և պացիենտի follow-up։": "AI-աջակցվող OPG վերլուծություն և պացիենտի հետագա վերահսկում։",

  /* Homepage / evidence */
  "Մեկ կլինիկական workspace՝ OPG-ների վերանայման, հնարավոր հայտնաբերումների կազմակերպման, պացիենտի համատեքստի պահպանման և follow-up գործողությունների վերահսկման համար։": "Մեկ կլինիկական աշխատանքային միջավայր՝ OPG-ների վերանայման, հնարավոր փոփոխությունների կազմակերպման, պացիենտի համատեքստի պահպանման և անհրաժեշտ հետագա վերահսկումները տեսանելի պահելու համար։",
  "Care-ը փակում է հետագա վերահսկման շղթան": "Հետագա վերահսկումը ամբողջացնում է կլինիկական շղթան",
  "Teta2-ի տեսանելի փաստերը ավելի օգտակար են, քան հորինված success rate-ը։": "Teta2-ի տեսանելի փաստերն ավելի օգտակար են, քան հորինված հաջողության ցուցանիշը։",
  "ԻՆՉՈՒ Է FOLLOW-UP-Ը ԿԱՐԵՎՈՐ": "ԻՆՉՈՒ Է ՀԵՏԱԳԱ ՎԵՐԱՀՍԿՈՒՄԸ ԿԱՐԵՎՈՐ",
  "Ռիսկը այն չէ, որ յուրաքանչյուր finding անպայման կդառնա ծանր։ Ռիսկն այն է, որ արդեն հայտնի կամ կասկածելի խնդիրը նկարի դիտումից հետո դուրս մնա կլինիկայի ուշադրությունից։": "Ռիսկն այն չէ, որ յուրաքանչյուր հնարավոր փոփոխություն անպայման կդառնա ծանր։ Ռիսկն այն է, որ արդեն հայտնի կամ կասկածելի խնդիրը նկարի դիտումից հետո դուրս մնա կլինիկայի ուշադրությունից։",

  /* Finding labels */
  "Apical change": "Ապիկալ փոփոխություն",
  "Apical periodontitis": "Ապիկալ պերիօդոնտիտ",
  "Bone loss": "Ոսկրային կորստի նշան",
  "Bone resorption": "Ոսկրային ռեզորբցիա",
  "Bridge": "Կամուրջ",
  "Caries": "Կարիես",
  "Crown": "Պսակ",
  "Deep caries": "Խորը կարիես",
  "Filling": "Լցոնում",
  "Furcation change": "Ֆուրկացիոն փոփոխություն",
  "Furcation lesion": "Ֆուրկացիոն ախտահարում",
  "Impacted tooth": "Չծկթած ատամ",
  "Implant": "Իմպլանտ",
  "Residual root": "Մնացորդային արմատ",
  "Restoration": "Վերականգնում",
  "Root canal treatment": "Արմատախողովակային բուժում",
  "Root canal filling": "Արմատախողովակային լցոնում",
  "Root fragment": "Արմատի հատված",
};

const RU: TextMap = {
  /* Dashboard shell */
  "Панель": "Главная",
  "ИИ-диалоги": "Диалоги с пациентами",
  "Teta2 · клиническое рабочее пространство": "Teta2 · рабочее пространство клинического наблюдения",
  "Ожидают подтверждения": "Ожидают вашего подтверждения",
  "Активные планы": "Активные планы наблюдения",
  "Активные диалоги": "Активные диалоги с пациентами",
  "Наблюдение сегодня": "Наблюдения к выполнению",
  "Проверьте план по каждому зубу до подтверждения связи с пациентом.": "Проверьте и при необходимости скорректируйте план по каждому зубу перед началом связи с пациентом.",
  "Подтвердить план и начать наблюдение": "Подтвердить план и начать связь с пациентом",
  "Диалоги WhatsApp, начатые после клинического подтверждения.": "Диалоги WhatsApp для последующего наблюдения начинаются после вашего клинического подтверждения.",
  "Предложенные пациентом даты остаются здесь до вашего подтверждения.": "Время осмотра, выбранное пациентом, остается здесь до вашего подтверждения.",

  /* OPG + AI */
  "No analysis selected": "Анализ не выбран",
  "Select an X-ray and run DENTAI V5.": "Выберите рентгеновский снимок и запустите DENTAI V5.",
  "Review saved.": "Результаты проверки сохранены.",
  "Analysis failed": "Не удалось выполнить анализ",
  "Interactive OPG": "Интерактивный OPG",
  "DENTAI clinical findings on the radiograph": "Клинические результаты DENTAI на рентгеновском снимке",
  "Green = treated or restored teeth · red = pathological findings · red intensity reflects model confidence.": "Зеленым отмечены пролеченные или восстановленные зубы · красным — возможные патологические изменения · интенсивность красного отражает уверенность модели.",
  "AI report": "Отчет ИИ",
  "AI overlay": "Слой ИИ",
  "All": "Все",
  "Pending": "Ожидает проверки",
  "Confirmed": "Подтверждено",
  "Rejected": "Отклонено",
  "The X-ray for this analysis is not available.": "Рентгеновский снимок для этого анализа недоступен.",
  "Loading radiograph…": "Загрузка рентгеновского снимка…",
  "The radiograph could not be loaded.": "Не удалось загрузить рентгеновский снимок.",
  "AI clinical report": "Клинический отчет ИИ",
  "Key observation": "Ключевое наблюдение",
  "Monitoring": "Наблюдение",
  "For the clinician": "Для врача",
  "AI summary does not replace clinician assessment.": "Резюме ИИ не заменяет оценку врача.",
  "Finding review filters": "Фильтры проверки результатов",
  "DENTAI clinical finding overlay": "Слой клинических результатов DENTAI",
  "This is an AI-assisted observation and is not a final diagnosis until reviewed by the clinician.": "Это наблюдение, сформированное с поддержкой ИИ, а не окончательный диагноз; результат должен проверить врач.",

  /* Follow-up generation */
  "AI FOLLOW-UP ORCHESTRATION": "УПРАВЛЕНИЕ ПОСЛЕДУЮЩИМ НАБЛЮДЕНИЕМ С ИИ",
  "Waiting for analysis to complete": "Ожидание завершения анализа",
  "The Generate button will unlock automatically as soon as the current OPG analysis finishes. No page refresh is required.": "Кнопка «Создать с ИИ» активируется автоматически после завершения текущего анализа OPG. Обновлять страницу не нужно.",
  "Generate with AI": "Создать с ИИ",
  "Follow-up plan ready": "План наблюдения готов",
  "Generate follow-up plan": "Создать план наблюдения",
  "No pathological tooth findings with a resolved FDI are available in this completed OPG analysis.": "В завершенном анализе OPG нет патологических изменений с определенным номером FDI, которые можно включить в план наблюдения.",
  "Checking pathological tooth eligibility with the care backend…": "Проверяем, какие зубы можно включить в план наблюдения…",
  "Open follow-up plans": "Открыть планы наблюдения",
  "Generating…": "Создание…",
  "Clinician review is recommended; doctor remains in control.": "Рекомендуется проверка врачом; окончательное решение остается за врачом.",
  "Doctor remains in control": "Окончательное решение остается за врачом",
  "Recommended: review AI findings before approving outreach, but generation is available now.": "Рекомендуется проверить результаты ИИ до начала связи с пациентом, однако план можно создать уже сейчас.",
  "No eligible pathological/red tooth findings are available in this completed OPG analysis.": "В завершенном анализе OPG нет патологических изменений, которые можно включить в план наблюдения.",

  /* Follow-up workspace */
  "CLINIC FOLLOW-UP QUEUE": "ОЧЕРЕДЬ ПОСЛЕДУЮЩЕГО НАБЛЮДЕНИЯ",
  "Patient follow-up plans": "Планы наблюдения пациентов",
  "One clinic WhatsApp connection serves all patients. Each patient keeps their own stored WhatsApp number and sequential tooth plan.": "Одно подключение WhatsApp клиники используется для всех пациентов. Номер WhatsApp и последовательный план по зубам хранятся отдельно для каждого пациента.",
  "patient plans": "планов пациентов",
  "Search patient, ID or WhatsApp": "Поиск по пациенту, номеру или WhatsApp",
  "Showing up to 200 recent plans": "Показаны до 200 последних планов",
  "No matching follow-up plans.": "Подходящих планов наблюдения не найдено.",
  "Patient": "Пациент",
  "Not registered": "Не указан",
  "Approve sequential outreach": "Подтвердить последовательную связь с пациентом",
  "Activating…": "Активация…",
  "Priority": "Приоритет",
  "AI finding": "Результат ИИ",
  "Conversation start:": "Начало диалога:",
  "After previous tooth outcome": "После итогового результата по предыдущему зубу",
  "Outcome:": "Результат:",
  "Clinical follow-up target": "Целевая дата клинического наблюдения",
  "Recommended window": "Рекомендуемый период",
  "Rationale": "Обоснование",
  "WhatsApp opening message": "Первое сообщение WhatsApp",
  "Saving…": "Сохранение…",
  "Save tooth plan": "Сохранить план по зубу",
  "CLINIC WHATSAPP": "WHATSAPP КЛИНИКИ",
  "Clinic WhatsApp connected": "WhatsApp клиники подключен",
  "Connect clinic WhatsApp": "Подключить WhatsApp клиники",
  "Connected": "Подключен",
  "Disconnected": "Не подключен",
  "Disconnect": "Отключить",
  "Connect with QR": "Подключить по QR-коду",
  "WHATSAPP LINKED DEVICE": "ПОДКЛЮЧЕНИЕ УСТРОЙСТВА WHATSAPP",
  "Scan with the clinic phone": "Отсканируйте телефоном клиники",
  "Generating secure QR…": "Создание защищенного QR-кода…",
  "WhatsApp → Linked devices → Link a device → scan this code.": "WhatsApp → Связанные устройства → Привязать устройство → отсканируйте этот код.",
  "LIVE AI CONVERSATION": "АКТИВНЫЙ ДИАЛОГ С ПОДДЕРЖКОЙ ИИ",
  "Patient conversation": "Диалог с пациентом",
  "Every WhatsApp message is mirrored here.": "Здесь отображается каждое сообщение WhatsApp.",
  "Live sync · 5s": "Синхронизация · 5 с",
  "APPOINTMENT AWAITING DOCTOR APPROVAL": "ПРИЕМ ОЖИДАЕТ ПОДТВЕРЖДЕНИЯ ВРАЧА",
  "CONVERSATION APPOINTMENT": "ПРИЕМ, СВЯЗАННЫЙ С ДИАЛОГОМ",
  "No messages for this patient yet.": "Для этого пациента сообщений пока нет.",
  "VISIT OUTCOME → AI FOLLOW-UP": "РЕЗУЛЬТАТ ПРИЕМА → ПОСЛЕДУЮЩЕЕ НАБЛЮДЕНИЕ С ИИ",
  "Appointment outcomes": "Итоги приемов",
  "Record what actually happened. Teta2 uses the outcome to continue the current tooth or unlock the next priority tooth.": "Зафиксируйте фактический результат приема. Teta2 использует его, чтобы продолжить этап по текущему зубу или открыть следующий приоритетный зуб.",
  "Optional clinical note": "Клиническая заметка (необязательно)",
  "Came · treated": "Пришел · лечение проведено",
  "Came · not treated": "Пришел · без лечения",
  "No-show": "Не явился",

  /* Case workspace */
  "Not scheduled": "Не запланировано",
  "Follow-up activated. The first outreach is scheduled; later teeth stay locked to the sequence.": "Наблюдение активировано. Первая связь запланирована; следующие зубы остаются заблокированными до завершения предыдущего этапа.",
  "FOLLOW-UP CASES": "СЛУЧАИ ПОСЛЕДУЮЩЕГО НАБЛЮДЕНИЯ",
  "Patient follow-up workspace": "Рабочее пространство наблюдения пациентов",
  "One patient = one organized case file. All dates are shown in the clinic timezone.": "Для каждого пациента ведется отдельное организованное дело. Все даты показаны в часовом поясе клиники.",
  "Clinic timezone": "Часовой пояс клиники",
  "No matching patient cases.": "Подходящих случаев не найдено.",
  "No follow-up case selected.": "Случай наблюдения не выбран.",
  "Clinic WhatsApp": "WhatsApp клиники",
  "QR connect": "Подключить по QR",
  "Close QR": "Закрыть QR",
  "Scan QR to connect": "Отсканируйте QR-код для подключения",
  "Generating QR…": "Создание QR-кода…",
  "PATIENT FOLLOW-UP FILE": "КАРТА ПОСЛЕДУЮЩЕГО НАБЛЮДЕНИЯ",
  "WhatsApp not registered": "WhatsApp не указан",
  "Approve outreach": "Подтвердить связь с пациентом",
  "Teeth in plan": "Зубов в плане",
  "Current tooth": "Текущий зуб",
  "First outreach": "Первая связь",
  "Timezone": "Часовой пояс",
  "FIRST WHATSAPP OUTREACH": "ПЕРВОЕ СООБЩЕНИЕ WHATSAPP",
  "Doctor can change this before the first message is sent": "Врач может изменить время до отправки первого сообщения",
  "Scheduled outreach": "Запланированная связь",
  "This controls when the AI sends the opening WhatsApp message for the first priority tooth.": "Здесь задается время, когда ИИ отправит первое сообщение WhatsApp по первому приоритетному зубу.",
  "Save send time": "Сохранить время отправки",
  "TREATMENT FOLLOW-UP SEQUENCE": "ПОСЛЕДОВАТЕЛЬНОСТЬ ПОСЛЕДУЮЩЕГО НАБЛЮДЕНИЯ",
  "Tooth-by-tooth plan": "План по каждому зубу",
  "Later teeth unlock only after the previous outcome.": "Следующий зуб становится доступен только после фиксации результата предыдущего этапа.",
  "Clinical follow-up": "Клиническое наблюдение",
  "Opening message will be prepared before outreach.": "Первое сообщение будет подготовлено до начала связи с пациентом.",

  /* Booking */
  "Loading live availability…": "Загрузка доступного времени…",
  "Booking link unavailable": "Ссылка для записи недоступна.",
  "Could not request appointment": "Не удалось отправить запрос на прием.",

  /* Public chrome/login */
  "Отказ от медицинских гарантий ИИ": "Ограничения клинического ИИ",
  "Use the clinic slug and account provisioned for your clinic.": "Используйте идентификатор клиники и учетную запись, полученные при активации.",
  "Clinic slug": "Идентификатор клиники",
  "SECURE CLINIC ACCESS": "БЕЗОПАСНЫЙ ДОСТУП ДЛЯ КЛИНИКИ",
  "Clinician-controlled · Patient-specific · Follow-up visible": "Под контролем врача · Для конкретного пациента · Наблюдение остается видимым",

  /* Access request */
  "Отправьте одну защищенную заявку. Страна в заявке автоматически определяет правильную цену и письмо при review.": "Отправьте одну защищенную заявку. Страна в заявке автоматически определит соответствующий рынок и цену при проверке.",
  "Funding Plan": "Льготный стартовый тариф",
  "первые 50 клиник": "для первых 50 клиник",
  "Standard": "Стандарт",
  "Рабочее пространство клиники сохраняется": "Рабочее пространство клиники сохраняется",
  "После окончания доступа workspace блокируется, а не удаляется. Продление возвращает те же данные и историю.": "После окончания доступа рабочее пространство блокируется, но не удаляется. Продление возвращает доступ к тем же данным и истории.",
  "Request submitted": "Заявка отправлена",
  "Your application is waiting for review. If approved, Teta2 will automatically select the Armenia or Russia pricing email from the country in your request.": "Ваша заявка ожидает проверки. После одобрения Teta2 применит цену для Армении или России в соответствии со страной, указанной в заявке.",
  "Back to Teta2": "Вернуться в Teta2",
  "Clinic name *": "Название клиники *",
  "Country *": "Страна *",
  "Select market": "Выберите рынок",
  "Armenia": "Армения",
  "Russia": "Россия",
  "City *": "Город *",
  "Pricing selected from country": "Цена определяется по стране",
  "Clinic address": "Адрес клиники",
  "Website": "Сайт",
  "Contact person *": "Контактное лицо *",
  "Role / title *": "Должность / роль *",
  "Director, owner, dentist…": "Директор, владелец, стоматолог…",
  "Email *": "Email *",
  "Phone *": "Телефон *",
  "Number of dentists *": "Количество стоматологов *",
  "Number of branches *": "Количество филиалов *",
  "Anything we should know?": "Что еще нам важно знать?",
  "Funding Plan availability is confirmed during review. Submission does not reserve a slot or activate access.": "Доступность льготного стартового тарифа подтверждается при проверке заявки. Отправка заявки не резервирует место и не активирует доступ.",
  "ИИ-анализ OPG и follow-up пациентов.": "ИИ-анализ OPG и последующее наблюдение пациентов.",

  /* Finding labels */
  "Apical change": "Апикальное изменение",
  "Apical periodontitis": "Апикальный периодонтит",
  "Bone loss": "Признак потери костной ткани",
  "Bone resorption": "Резорбция костной ткани",
  "Bridge": "Мостовидный протез",
  "Caries": "Кариес",
  "Crown": "Коронка",
  "Deep caries": "Глубокий кариес",
  "Filling": "Пломба",
  "Furcation change": "Изменение в области фуркации",
  "Furcation lesion": "Поражение фуркации",
  "Impacted tooth": "Ретинированный зуб",
  "Implant": "Имплантат",
  "Residual root": "Остаточный корень",
  "Restoration": "Реставрация",
  "Root canal treatment": "Эндодонтическое лечение",
  "Root canal filling": "Пломбирование корневого канала",
  "Root fragment": "Фрагмент корня",
};

const STATUS_HY: TextMap = {
  "Pending Approval": "Սպասում է հաստատման",
  "Active": "Ակտիվ",
  "Paused": "Դադարեցված",
  "Completed": "Ավարտված",
  "Followup Ready": "Պատրաստ է հետագա վերահսկման",
  "Waiting Previous Tooth": "Սպասում է նախորդ ատամի փուլին",
  "Contacted": "Կապ է հաստատվել",
  "Booked": "Ամրագրված",
  "Proposed": "Առաջարկված",
  "Approved": "Հաստատված",
  "Confirmed": "Հաստատված",
  "Rejected": "Մերժված",
  "Cancelled": "Չեղարկված",
  "Treated": "Բուժված",
  "Attended Not Treated": "Այցելել է՝ առանց բուժման",
  "No Show": "Չի ներկայացել",
  "Pending": "Սպասման մեջ",
  "Sending": "Ուղարկվում է",
  "Sent": "Ուղարկված",
  "Failed": "Չհաջողվեց",
  "Queued": "Հերթում",
  "Processing": "Մշակվում է",
  "Unreviewed": "Չվերանայված",
  "Reviewed": "Վերանայված",
  "Followup Ready": "Պատրաստ է հետագա վերահսկման",
};

const STATUS_RU: TextMap = {
  "Pending Approval": "Ожидает подтверждения",
  "Active": "Активен",
  "Paused": "Приостановлен",
  "Completed": "Завершен",
  "Followup Ready": "Готов к наблюдению",
  "Waiting Previous Tooth": "Ожидает завершения предыдущего зуба",
  "Contacted": "Связь установлена",
  "Booked": "Записан",
  "Proposed": "Предложено",
  "Approved": "Подтверждено",
  "Confirmed": "Подтверждено",
  "Rejected": "Отклонено",
  "Cancelled": "Отменено",
  "Treated": "Лечение проведено",
  "Attended Not Treated": "Прием состоялся без лечения",
  "No Show": "Не явился",
  "Pending": "Ожидает",
  "Sending": "Отправляется",
  "Sent": "Отправлено",
  "Failed": "Ошибка",
  "Queued": "В очереди",
  "Processing": "Обрабатывается",
  "Unreviewed": "Не проверено",
  "Reviewed": "Проверено",
};

const LEGAL_HY: TextMap = {
  "Trust center": "Իրավական և վստահության կենտրոն",
  "LEGAL & TRUST": "ԻՐԱՎԱԿԱՆ ԵՎ ՎՍՏԱՀՈՒԹՅՈՒՆ",
  "TRANSPARENCY": "ԹԱՓԱՆՑԻԿՈՒԹՅՈՒՆ",
  "COMMERCIAL TERMS": "ԱՌԵՎՏՐԱՅԻՆ ՊԱՅՄԱՆՆԵՐ",
  "CLINICAL SAFETY": "ԿԼԻՆԻԿԱԿԱՆ ԱՆՎՏԱՆԳՈՒԹՅՈՒՆ",
  "How Teta2 handles clinic applications, account information, patient records, OPG images and clinical workflow data.": "Ինչպես է Teta2-ը մշակում կլինիկայի հայտերը, հաշվի տվյալները, պացիենտների քարտերը, OPG պատկերները և կլինիկական գործընթացի տվյալները։",
  "1. Scope and roles": "1. Կիրառման շրջանակը և դերերը",
  "This policy applies to teta2.com, the clinic dashboard and the Teta2 access-request process. For clinic patient data, the clinic determines why the data is used and is normally the data controller; Teta2 processes that data to provide the contracted platform. For access requests, account administration, security and support, Teta2 determines the relevant processing purposes.": "Այս քաղաքականությունը կիրառվում է teta2.com կայքի, կլինիկայի վահանակի և Teta2 մուտքի հայտերի գործընթացի նկատմամբ։ Կլինիկայի պացիենտների տվյալների դեպքում կլինիկան որոշում է տվյալների օգտագործման նպատակը և սովորաբար հանդես է գալիս որպես տվյալների պատասխանատու, իսկ Teta2-ը մշակում է դրանք պայմանագրային հարթակը տրամադրելու համար։ Մուտքի հայտերի, հաշիվների կառավարման, անվտանգության և աջակցության դեպքում մշակման համապատասխան նպատակները որոշում է Teta2-ը։",
  "2. Information processed": "2. Մշակվող տեղեկությունները",
  "Teta2 processes only information provided through the service or generated by its operation.": "Teta2-ը մշակում է միայն ծառայության միջոցով տրամադրված կամ դրա աշխատանքի ընթացքում ստեղծված տեղեկությունները։",
  "Clinic application details: clinic name, country, city, address if supplied, website, contact person, role, email, phone, number of dentists and branches, and notes.": "Կլինիկայի հայտի տվյալներ՝ կլինիկայի անվանում, երկիր, քաղաք, տրամադրման դեպքում՝ հասցե և կայք, կոնտակտային անձ, դեր, էլ․ փոստ, հեռախոս, ատամնաբույժների և մասնաճյուղերի քանակ, ինչպես նաև նշումներ։",
  "Account and access data: username, email, role, clinic and branch permissions, authentication tokens and security events.": "Հաշվի և մուտքի տվյալներ՝ օգտանուն, էլ․ փոստ, դեր, կլինիկայի և մասնաճյուղերի թույլտվություններ, նույնականացման նշաններ և անվտանգության իրադարձություններ։",
  "Patient and clinical data entered by an authorized clinic: identifiers, contact details, date of birth, sex, clinical records, OPG images, AI-assisted possible findings, clinician reviews, follow-up plans, messages and appointments.": "Լիազորված կլինիկայի մուտքագրած պացիենտի և կլինիկական տվյալներ՝ նույնականացուցիչներ, կոնտակտային տվյալներ, ծննդյան ամսաթիվ, սեռ, կլինիկական գրառումներ, OPG պատկերներ, AI-աջակցվող հնարավոր փոփոխություններ, բժշկի վերանայումներ, հետագա վերահսկման պլաններ, հաղորդագրություններ և այցեր։",
  "Operational data: request identifiers, timestamps, delivery states, audit records and limited network/security metadata.": "Գործառնական տվյալներ՝ հարցումների նույնականացուցիչներ, ժամանակային նշումներ, առաքման կարգավիճակներ, աուդիտի գրառումներ և սահմանափակ ցանցային/անվտանգության մետատվյալներ։",
  "Payment administration data: payment reference, receipt notes, verification status and related correspondence. Teta2 does not currently collect payment-card data through an online checkout.": "Վճարումների կառավարման տվյալներ՝ վճարման հղում կամ նույնականացուցիչ, անդորրագրի նշումներ, ստուգման կարգավիճակ և համապատասխան հաղորդակցություն։ Teta2-ը ներկայում առցանց վճարման ձևով չի հավաքում վճարային քարտերի տվյալներ։",
  "3. Purposes and legal grounds": "3. Նպատակները և իրավական հիմքերը",
  "Information is used to review access requests, create and secure clinic workspaces, provide OPG and follow-up functions, deliver support, administer subscriptions and payments, prevent misuse, maintain auditability and comply with applicable law. Processing is based, as applicable, on performance of the service agreement, steps requested before entering that agreement, legitimate security and operational interests, legal obligations, and the clinic's lawful authority to process patient information.": "Տեղեկություններն օգտագործվում են մուտքի հայտերը ստուգելու, կլինիկայի աշխատանքային միջավայրը ստեղծելու և պաշտպանելու, OPG ու հետագա վերահսկման գործառույթները տրամադրելու, աջակցություն մատուցելու, բաժանորդագրություններն ու վճարումները կառավարելու, չարաշահումները կանխելու, աուդիտային հետագծելիությունն ապահովելու և կիրառելի օրենսդրությանը համապատասխանելու համար։ Մշակման հիմքերը, ըստ կիրառելիության, ներառում են ծառայության պայմանագրի կատարումը, պայմանագրի կնքումից առաջ պահանջված քայլերը, անվտանգության և գործառնական օրինական շահերը, իրավական պարտավորությունները և պացիենտների տվյալները մշակելու կլինիկայի օրինական իրավասությունը։",
  "4. Infrastructure and recipients": "4. Ենթակառուցվածքը և տվյալների ստացողները",
  "The production service uses infrastructure providers to host the frontend, application services and databases. The PostgreSQL database is hosted on AWS infrastructure. Authorized service providers receive only the information needed for hosting, email delivery, secure file storage or clinic-enabled messaging. When a clinic connects or uses WhatsApp, message and recipient information is also handled under the applicable WhatsApp/Meta terms. Teta2 does not sell patient or clinic personal data.": "Արտադրական ծառայությունն օգտագործում է ենթակառուցվածքային մատակարարներ՝ ֆրոնտենդը, հավելվածի ծառայություններն ու տվյալների բազաները հոսթինգի համար։ PostgreSQL տվյալների բազան տեղակայված է AWS ենթակառուցվածքում։ Լիազորված ծառայությունների մատակարարները ստանում են միայն հոսթինգի, էլ․ փոստի առաքման, անվտանգ ֆայլային պահոցի կամ կլինիկայի միացրած հաղորդագրությունների համար անհրաժեշտ տեղեկությունները։ Երբ կլինիկան միացնում կամ օգտագործում է WhatsApp-ը, հաղորդագրությունների և ստացողների տվյալները նույնպես մշակվում են WhatsApp/Meta-ի կիրառելի պայմանների համաձայն։ Teta2-ը չի վաճառում պացիենտների կամ կլինիկաների անձնական տվյալները։",
  "5. Retention": "5. Պահպանման ժամկետը",
  "Data is retained while the clinic workspace is active and afterward where needed to preserve the clinic record, meet legal or security obligations, resolve disputes or support renewal. Subscription expiry locks access; it does not automatically delete clinic data. A clinic may request closure or deletion at the contact address below. Requests are assessed against the clinic's instructions, patient-safety needs and mandatory retention duties. Browser session tokens are removed when the browser session ends or the user signs out.": "Տվյալները պահպանվում են կլինիկայի աշխատանքային միջավայրի ակտիվ լինելու ընթացքում և դրանից հետո՝ այնքանով, որքանով անհրաժեշտ է կլինիկայի գրառումները պահպանելու, իրավական կամ անվտանգության պարտավորությունները կատարելու, վեճերը լուծելու կամ երկարաձգումն ապահովելու համար։ Բաժանորդագրության ավարտը կողպում է մուտքը, բայց ինքնաբերաբար չի ջնջում կլինիկայի տվյալները։ Կլինիկան կարող է ստորև նշված հասցեով պահանջել աշխատանքային միջավայրի փակում կամ տվյալների ջնջում։ Հարցումները գնահատվում են կլինիկայի ցուցումների, պացիենտի անվտանգության կարիքների և պարտադիր պահպանման պահանջների համատեքստում։ Դիտարկչի աշխատաշրջանի նշանները հեռացվում են աշխատաշրջանի ավարտից կամ օգտատիրոջ դուրս գալուց հետո։",
  "6. Security": "6. Անվտանգություն",
  "Teta2 uses access controls, tenant separation, protected transport, encrypted credential handling, audit records and restricted administrative access. No online service can promise absolute security. Clinics must keep credentials confidential, use authorized devices and report suspected access promptly.": "Teta2-ը կիրառում է մուտքի վերահսկում, կլինիկաների տվյալների տարանջատում, պաշտպանված փոխանցում, նույնականացման տվյալների կոդավորված մշակում, աուդիտի գրառումներ և սահմանափակ վարչական մուտք։ Ոչ մի առցանց ծառայություն չի կարող երաշխավորել բացարձակ անվտանգություն։ Կլինիկաները պարտավոր են մուտքի տվյալները գաղտնի պահել, օգտագործել լիազորված սարքեր և անհապաղ հայտնել կասկածելի մուտքի մասին։",
  "7. Rights and clinic responsibilities": "7. Իրավունքները և կլինիկայի պարտականությունները",
  "Under applicable Armenian data-protection law, individuals may request information about processing and, where applicable, access, correction, blocking or deletion. Patient requests should normally be directed to the treating clinic because the clinic controls the patient record. Teta2 will assist the clinic where required. Clinics must have a lawful basis and provide any required patient notice before uploading personal or clinical data.": "Հայաստանի տվյալների պաշտպանության կիրառելի օրենսդրության համաձայն՝ անձինք կարող են պահանջել տեղեկություն մշակման մասին և, կիրառելի դեպքերում, մուտք, ուղղում, արգելափակում կամ ջնջում։ Պացիենտների հարցումները սովորաբար պետք է ուղղվեն բուժող կլինիկային, քանի որ պացիենտի քարտը վերահսկում է կլինիկան։ Անհրաժեշտության դեպքում Teta2-ը կաջակցի կլինիկային։ Անձնական կամ կլինիկական տվյալներ վերբեռնելուց առաջ կլինիկան պետք է ունենա օրինական հիմք և պացիենտին տրամադրի պահանջվող ծանուցումները։",
  "8. International processing and changes": "8. Միջազգային մշակում և փոփոխություններ",
  "Service providers may process data outside the individual's country. Teta2 uses contractual and technical safeguards appropriate to the service and applicable law. Material policy changes will be posted on this page with a revised date.": "Ծառայությունների մատակարարները կարող են տվյալներ մշակել անձի երկրից դուրս։ Teta2-ը կիրառում է ծառայությանը և կիրառելի օրենսդրությանը համապատասխան պայմանագրային ու տեխնիկական պաշտպանական միջոցներ։ Քաղաքականության էական փոփոխությունները կհրապարակվեն այս էջում՝ թարմացված ամսաթվով։",

  "The rules governing access to and use of the Teta2 clinical software platform.": "Teta2 կլինիկական ծրագրային հարթակ մուտք գործելու և այն օգտագործելու կանոնները։",
  "1. Agreement and eligibility": "1. Համաձայնություն և իրավասություն",
  "By requesting access, paying for a subscription or using a clinic workspace, the clinic and its authorized users agree to these Terms. The person accepting must be legally able to act for the clinic. Teta2 is intended for professional dental-clinic use, not direct patient self-diagnosis or emergency care.": "Մուտք խնդրելով, բաժանորդագրության համար վճարելով կամ կլինիկայի աշխատանքային միջավայրն օգտագործելով՝ կլինիկան և նրա լիազորված օգտատերերը համաձայնում են այս պայմաններին։ Համաձայնություն տվող անձը պետք է իրավասու լինի գործել կլինիկայի անունից։ Teta2-ը նախատեսված է ատամնաբուժական կլինիկաների մասնագիտական օգտագործման համար և նախատեսված չէ պացիենտների ինքնուրույն ախտորոշման կամ շտապ բուժօգնության համար։",
  "2. Access and subscription": "2. Մուտք և բաժանորդագրություն",
  "Public self-service activation is not currently available. Teta2 reviews each application, sends payment instructions when approved, verifies payment manually and then issues clinic credentials. The subscription period and price are those shown in the approved offer or payment instructions. The current standard activation flow provisions a fixed 30-day period. Renewal restores access to the same workspace unless otherwise agreed.": "Հանրային ինքնուրույն ակտիվացումը ներկայում հասանելի չէ։ Teta2-ը ստուգում է յուրաքանչյուր հայտ, հաստատումից հետո ուղարկում վճարման հրահանգները, ձեռքով ստուգում վճարումը և ապա տրամադրում կլինիկայի մուտքի տվյալները։ Բաժանորդագրության ժամկետն ու գինը նշված են հաստատված առաջարկում կամ վճարման հրահանգներում։ Ներկայիս ստանդարտ ակտիվացումը նախատեսում է ֆիքսված 30-օրյա ժամկետ։ Երկարաձգումը վերականգնում է նույն աշխատանքային միջավայրի մուտքը, եթե այլ բան համաձայնեցված չէ։",
  "3. Clinical responsibility": "3. Կլինիկական պատասխանատվություն",
  "Teta2 provides workflow software and AI-assisted possible findings. It does not provide a final diagnosis, treatment decision or substitute for examination by a qualified dentist. The clinic remains responsible for clinical review, patient consent, diagnosis, treatment, communications and compliance with professional rules.": "Teta2-ը տրամադրում է կլինիկական գործընթացի ծրագրային գործիքներ և AI-աջակցվող հնարավոր փոփոխություններ։ Այն չի տալիս վերջնական ախտորոշում կամ բուժման որոշում և չի փոխարինում որակավորված ատամնաբույժի զննմանը։ Կլինիկան շարունակում է պատասխանատու լինել կլինիկական վերանայման, պացիենտի համաձայնության, ախտորոշման, բուժման, հաղորդակցության և մասնագիտական կանոնների պահպանման համար։",
  "4. Clinic obligations": "4. Կլինիկայի պարտականությունները",
  "The clinic must provide accurate information, use patient data lawfully, limit access to authorized staff, protect credentials, review AI output before relying on it and keep its own legally required clinical records. The clinic must not upload data it is not authorized to process.": "Կլինիկան պարտավոր է տրամադրել ճշգրիտ տեղեկություններ, պացիենտների տվյալներն օգտագործել օրինականորեն, մուտքը սահմանափակել լիազորված աշխատակիցներով, պաշտպանել մուտքի տվյալները, AI արդյունքը վերանայել մինչև դրա վրա հիմնվելը և վարել օրենքով պահանջվող իր կլինիկական գրառումները։ Կլինիկան չպետք է վերբեռնի տվյալներ, որոնք մշակելու իրավասություն չունի։",
  "5. Acceptable use": "5. Թույլատրելի օգտագործում",
  "Users may not attempt unauthorized access, bypass tenant controls, probe or overload the service, reverse engineer protected components, upload malicious or unlawful content, use the system to make unsupervised clinical decisions, or use ordinary clinic access for automated bulk processing or resale. Fair-use limits may be applied to abnormal automation or API abuse.": "Օգտատերերը չեն կարող փորձել չարտոնված մուտք ստանալ, շրջանցել կլինիկաների տարանջատման վերահսկումները, փորձարկել կամ գերբեռնել ծառայությունը, հետադարձ ինժեներիայով ուսումնասիրել պաշտպանված բաղադրիչները, վերբեռնել վնասակար կամ անօրինական բովանդակություն, համակարգն օգտագործել առանց բժշկի վերահսկման կլինիկական որոշումների համար կամ սովորական կլինիկայի մուտքն օգտագործել ավտոմատ զանգվածային մշակման կամ վերավաճառքի նպատակով։ Աննորմալ ավտոմատացման կամ API չարաշահման դեպքում կարող են կիրառվել արդար օգտագործման սահմանափակումներ։",
  "6. Messaging and third parties": "6. Հաղորդագրություններ և երրորդ կողմեր",
  "Clinic-enabled WhatsApp messaging depends on the clinic's connected account and third-party availability. The clinic is responsible for lawful recipient consent, message content and communication timing. Third-party services remain subject to their own terms and may change independently of Teta2.": "Կլինիկայի միացրած WhatsApp հաղորդագրությունները կախված են կլինիկայի կապակցված հաշվից և երրորդ կողմի ծառայության հասանելիությունից։ Կլինիկան պատասխանատու է ստացողի օրինական համաձայնության, հաղորդագրության բովանդակության և հաղորդակցության ժամանակի համար։ Երրորդ կողմի ծառայությունները գործում են իրենց պայմաններով և կարող են փոխվել Teta2-ից անկախ։",
  "7. Availability, suspension and termination": "7. Հասանելիություն, կասեցում և դադարեցում",
  "Teta2 may perform maintenance and cannot guarantee uninterrupted availability. Access may be suspended for non-payment, expired subscription, security risk, unlawful use or material breach. The clinic may stop using the service and request workspace closure by email. Data handling after expiry or closure follows the Privacy Policy and applicable law.": "Teta2-ը կարող է կատարել տեխնիկական սպասարկում և չի կարող երաշխավորել անընդհատ հասանելիություն։ Մուտքը կարող է կասեցվել չվճարման, բաժանորդագրության ավարտի, անվտանգության ռիսկի, անօրինական օգտագործման կամ էական խախտման դեպքում։ Կլինիկան կարող է դադարեցնել ծառայության օգտագործումը և էլ․ փոստով խնդրել փակել աշխատանքային միջավայրը։ Ժամկետի ավարտից կամ փակումից հետո տվյալների մշակումը կատարվում է Գաղտնիության քաղաքականության և կիրառելի օրենսդրության համաձայն։",
  "8. Intellectual property and feedback": "8. Մտավոր սեփականություն և արձագանք",
  "Teta2 and its software, interface and platform materials remain protected by applicable intellectual-property law. Clinics retain their rights in clinic and patient data. A subscription grants a limited, non-exclusive, non-transferable right to use the service during the active period. Feedback may be used to improve the platform without identifying patients or disclosing clinic-confidential information.": "Teta2-ը, դրա ծրագրային ապահովումը, միջերեսը և հարթակի նյութերը պաշտպանվում են կիրառելի մտավոր սեփականության օրենսդրությամբ։ Կլինիկաները պահպանում են իրենց իրավունքները կլինիկայի և պացիենտների տվյալների նկատմամբ։ Բաժանորդագրությունը տալիս է ծառայությունն ակտիվ ժամանակահատվածում օգտագործելու սահմանափակ, ոչ բացառիկ և չփոխանցվող իրավունք։ Արձագանքը կարող է օգտագործվել հարթակը բարելավելու համար՝ առանց պացիենտներին նույնականացնելու կամ կլինիկայի գաղտնի տեղեկությունները բացահայտելու։",
  "9. Liability and law": "9. Պատասխանատվություն և կիրառելի իրավունք",
  "To the extent permitted by law, Teta2 is not liable for clinical decisions, missed diagnoses, treatment outcomes, third-party messaging failures or losses caused by unauthorized clinic use. Nothing in these Terms excludes liability that cannot lawfully be excluded. Disputes should first be raised at the support email for good-faith resolution.": "Օրենքով թույլատրելի սահմաններում Teta2-ը պատասխանատվություն չի կրում կլինիկական որոշումների, բաց թողնված ախտորոշումների, բուժման արդյունքների, երրորդ կողմի հաղորդագրությունների ձախողումների կամ կլինիկայի չարտոնված օգտագործմամբ առաջացած կորուստների համար։ Այս պայմաններում ոչինչ չի բացառում այն պատասխանատվությունը, որը օրենքով չի կարող բացառվել։ Վեճերի դեպքում նախ պետք է կապվել աջակցության էլ․ փոստով՝ բարեխիղճ լուծում գտնելու նպատակով։",

  "A precise list of what the current Teta2 frontend stores in your browser.": "Ճշգրիտ ցանկ այն տվյալների, որոնք Teta2-ի ներկայիս ֆրոնտենդը պահում է ձեր դիտարկչում։",
  "Teta2 currently uses no advertising or analytics cookies and no cookie-based tracking banner is required for those purposes.": "Teta2-ը ներկայում չի օգտագործում գովազդային կամ վերլուծական քուքիներ, ուստի այդ նպատակների համար քուքիների վրա հիմնված հետևման համաձայնության պատուհան չի պահանջվում։",
  "1. Current storage": "1. Ներկայում օգտագործվող պահոցը",
  "The public frontend uses browser storage only for essential preferences and session operation.": "Հանրային ֆրոնտենդը դիտարկչի պահոցն օգտագործում է միայն անհրաժեշտ կարգավորումների և աշխատաշրջանի աշխատանքի համար։",
  "Language preference (`teta2-product-language` and compatibility key `teta2-v4-language`) is stored in localStorage so the selected language remains on the device.": "Լեզվի ընտրությունը (`teta2-product-language` և համատեղելիության `teta2-v4-language` բանալիները) պահվում է localStorage-ում, որպեսզի ընտրված լեզուն պահպանվի սարքում։",
  "The acknowledgement of the essential-storage notice (`teta2-storage-notice-v1`) is stored in localStorage.": "Անհրաժեշտ պահոցի մասին ծանուցման ընդունումը (`teta2-storage-notice-v1`) պահվում է localStorage-ում։",
  "Clinic authentication tokens are stored in sessionStorage and are intended to last only for the active browser session.": "Կլինիկայի նույնականացման նշանները պահվում են sessionStorage-ում և նախատեսված են միայն դիտարկչի ընթացիկ աշխատաշրջանի համար։",
  "Platform-administrator session data, where applicable, is also stored in sessionStorage.": "Հարթակի ադմինիստրատորի աշխատաշրջանի տվյալները, կիրառելի դեպքում, նույնպես պահվում են sessionStorage-ում։",
  "2. What is not used": "2. Ինչ չի օգտագործվում",
  "The current Teta2 frontend does not include Google Analytics, Meta Pixel, PostHog, advertising cookies or cross-site behavioural tracking. Teta2 does not use the essential storage listed above to build advertising profiles.": "Teta2-ի ներկայիս ֆրոնտենդը չի ներառում Google Analytics, Meta Pixel, PostHog, գովազդային քուքիներ կամ կայքերի միջև վարքագծային հետևում։ Վերը նշված անհրաժեշտ պահոցը Teta2-ը չի օգտագործում գովազդային պրոֆիլներ ստեղծելու համար։",
  "3. Your controls": "3. Ձեր վերահսկման հնարավորությունները",
  "You can clear localStorage and sessionStorage through your browser settings. Clearing language storage resets the language choice. Clearing session storage signs the user out. Blocking essential browser storage may prevent sign-in or preference persistence. If non-essential analytics or advertising technology is introduced later, this policy and the consent interface must be updated before that technology is activated.": "Դուք կարող եք դիտարկչի կարգավորումներից մաքրել localStorage-ն ու sessionStorage-ը։ Լեզվի պահոցը մաքրելիս լեզվի ընտրությունը վերականգնվում է սկզբնական վիճակին, իսկ sessionStorage-ը մաքրելիս օգտատերը դուրս է գալիս հաշվից։ Անհրաժեշտ դիտարկչային պահոցն արգելափակելը կարող է խանգարել մուտքին կամ կարգավորումների պահպանմանը։ Եթե հետագայում ներդրվեն ոչ անհրաժեշտ վերլուծական կամ գովազդային տեխնոլոգիաներ, այս քաղաքականությունն ու համաձայնության միջերեսը պետք է թարմացվեն մինչև դրանց ակտիվացումը։",

  "How the current clinic subscription payment process actually works.": "Ինչպես է իրականում աշխատում կլինիկայի ներկայիս բաժանորդագրության վճարման գործընթացը։",
  "Teta2 does not currently operate an online card checkout or name Stripe, PayPal or another gateway as its payment processor.": "Teta2-ը ներկայում չի օգտագործում առցանց քարտային վճարման էջ և Stripe-ը, PayPal-ը կամ որևէ այլ վճարային դարպաս չի ներկայացնում որպես իր վճարային պրոցեսոր։",
  "1. Approved payment flow": "1. Հաստատված վճարման ընթացքը",
  "A clinic first submits an access request. If approved, Teta2 sends the price, subscription period, recipient and payment instructions to the email supplied by the clinic. The clinic then sends its receipt or payment reference. Access is activated only after an administrator verifies payment. Never send money using details received from an unverified source; confirm unusual instructions through teta2support@gmail.com.": "Կլինիկան նախ ուղարկում է մուտքի հայտ։ Հաստատվելու դեպքում Teta2-ը կլինիկայի տրամադրած էլ․ փոստին ուղարկում է գինը, բաժանորդագրության ժամկետը, ստացողի տվյալները և վճարման հրահանգները։ Այնուհետև կլինիկան ուղարկում է անդորրագիրը կամ վճարման նույնականացուցիչը։ Մուտքն ակտիվացվում է միայն ադմինիստրատորի կողմից վճարումը ստուգելուց հետո։ Երբեք գումար մի փոխանցեք չստուգված աղբյուրից ստացված տվյալներով․ անսովոր հրահանգները հաստատեք teta2support@gmail.com հասցեով։",
  "2. Price, currency and activation": "2. Գին, արժույթ և ակտիվացում",
  "The binding amount and currency are those in the written payment instruction sent for that clinic. Prices displayed publicly are informational until the request is approved. The standard activation period is 30 days unless the written offer states otherwise. Failed, incomplete or unverifiable transfers do not activate access.": "Պարտադիր համարվող գումարն ու արժույթը տվյալ կլինիկային ուղարկված գրավոր վճարման հրահանգներում նշվածներն են։ Հանրային ցուցադրվող գները տեղեկատվական են մինչև հայտի հաստատումը։ Ստանդարտ ակտիվացման ժամկետը 30 օր է, եթե գրավոր առաջարկում այլ բան նշված չէ։ Չհաջողված, թերի կամ չստուգվող փոխանցումները մուտք չեն ակտիվացնում։",
  "3. Cancellations and refunds": "3. Չեղարկումներ և վերադարձներ",
  "Because there is no automatic checkout, cancellation and refund eligibility must be stated in the written payment terms provided before payment. If those instructions do not address a refund situation, contact support promptly with the clinic name, payer, date, amount and payment reference. Teta2 will review the request against the agreed terms, whether access was activated or used, service-delivery evidence and any non-waivable rights under Armenian law. This page does not promise an automatic refund or remove rights that cannot legally be waived.": "Քանի որ ավտոմատ վճարման համակարգ չկա, չեղարկման և գումարի վերադարձի իրավասությունը պետք է նշված լինի վճարումից առաջ տրամադրված գրավոր պայմաններում։ Եթե այդ հրահանգները չեն անդրադառնում վերադարձի կոնկրետ դեպքին, անհապաղ կապվեք աջակցության հետ՝ նշելով կլինիկայի անունը, վճարողին, ամսաթիվը, գումարը և վճարման նույնականացուցիչը։ Teta2-ը հարցումը կգնահատի համաձայնեցված պայմանների, մուտքի ակտիվացման կամ օգտագործման փաստի, ծառայության մատուցման ապացույցների և Հայաստանի օրենսդրությամբ չհրաժարվող իրավունքների հիման վրա։ Այս էջը չի խոստանում ավտոմատ վերադարձ և չի վերացնում այն իրավունքները, որոնցից օրենքով հնարավոր չէ հրաժարվել։",
  "4. Expiry and renewal": "4. Ժամկետի ավարտ և երկարաձգում",
  "At expiry, dashboard access is locked rather than the clinic workspace being automatically deleted. Renewal can restore the same clinic workspace and retained records, subject to the Privacy Policy, applicable law and any updated written offer.": "Ժամկետի ավարտին վահանակի մուտքը կողպվում է, իսկ կլինիկայի աշխատանքային միջավայրը ինքնաբերաբար չի ջնջվում։ Երկարաձգումը կարող է վերականգնել նույն աշխատանքային միջավայրն ու պահպանված գրառումները՝ Գաղտնիության քաղաքականության, կիրառելի օրենսդրության և ցանկացած թարմացված գրավոր առաջարկի պայմաններով։",

  "The boundaries of Teta2's OPG analysis and follow-up assistance.": "Teta2-ի OPG վերլուծության և հետագա վերահսկման աջակցության սահմանները։",
  "Teta2 is clinical decision-support software. AI output is a possible finding—not a diagnosis.": "Teta2-ը կլինիկական որոշումների աջակցման ծրագրային գործիք է։ AI-ի արդյունքը հնարավոր փոփոխություն է, ոչ ախտորոշում։",
  "1. Qualified professional review required": "1. Պահանջվում է որակավորված մասնագետի վերանայում",
  "Every image, highlight, label, report, priority or follow-up suggestion must be reviewed by a qualified dental professional together with the original OPG, examination, history and any additional imaging. A user must not treat model output as confirmed disease or absence of disease.": "Յուրաքանչյուր պատկեր, նշում, պիտակ, զեկույց, առաջնահերթություն կամ հետագա վերահսկման առաջարկ պետք է վերանայի որակավորված ատամնաբույժը՝ սկզբնական OPG-ի, կլինիկական զննման, պատմության և անհրաժեշտ լրացուցիչ պատկերների հետ միասին։ Օգտատերը չպետք է մոդելի արդյունքը համարի հաստատված հիվանդություն կամ հիվանդության բացակայության ապացույց։",
  "2. Known limitations": "2. Հայտնի սահմանափակումներ",
  "AI can miss findings, mark normal anatomy, localize the wrong tooth or region, misread image artifacts and produce incomplete or incorrect text. Performance can vary with devices, positioning, exposure, anatomy, restorations, pathology and populations. Teta2 does not claim perfect or universally validated diagnostic accuracy.": "AI-ը կարող է բաց թողնել փոփոխություններ, սխալ նշել նորմալ անատոմիական կառուցվածքները, սխալ տեղորոշել ատամը կամ շրջանը, սխալ մեկնաբանել պատկերի արտեֆակտները և ստեղծել թերի կամ սխալ տեքստ։ Արդյունավետությունը կարող է տարբերվել սարքից, դիրքավորումից, էքսպոզիցիայից, անատոմիայից, վերականգնումներից, պաթոլոգիայից և պացիենտների խմբերից կախված։ Teta2-ը չի պնդում կատարյալ կամ համընդհանուր վավերացված ախտորոշիչ ճշգրտություն։",
  "3. Not for emergencies or autonomous care": "3. Նախատեսված չէ շտապ դեպքերի կամ ինքնավար բուժօգնության համար",
  "Teta2 is not an emergency service and must not delay urgent assessment. It must not autonomously diagnose, prescribe, select treatment or send clinical claims to a patient without the clinic's appropriate review and authority. The treating clinician remains responsible for the final record and care decision.": "Teta2-ը շտապ օգնության ծառայություն չէ և չպետք է հետաձգի հրատապ մասնագիտական գնահատումը։ Այն չպետք է ինքնուրույն ախտորոշի, դեղատոմս նշանակի, ընտրի բուժում կամ պացիենտին ուղարկի կլինիկական պնդումներ՝ առանց կլինիկայի համապատասխան վերանայման և իրավասության։ Բուժող բժիշկը շարունակում է պատասխանատու լինել վերջնական գրառման և բուժման որոշման համար։",
  "4. Follow-up and messaging": "4. Հետագա վերահսկում և հաղորդագրություններ",
  "Priorities, schedules and messages support clinic workflow; they do not guarantee patient contact, attendance or outcome. Clinics must verify recipient identity, consent, message accuracy, urgency and suitable escalation. WhatsApp and other delivery services may fail or be unavailable independently of Teta2.": "Առաջնահերթությունները, ժամանակացույցերը և հաղորդագրությունները աջակցում են կլինիկայի աշխատանքային գործընթացին, բայց չեն երաշխավորում պացիենտի հետ կապը, այցը կամ կլինիկական արդյունքը։ Կլինիկան պետք է ստուգի ստացողի ինքնությունը, համաձայնությունը, հաղորդագրության ճշգրտությունը, հրատապությունը և անհրաժեշտ էսկալացիան։ WhatsApp-ը և այլ առաքման ծառայություններ կարող են խափանվել կամ անհասանելի լինել Teta2-ից անկախ։",
};

const LEGAL_RU: TextMap = {
  "Trust center": "Центр доверия и правовой информации",
  "LEGAL & TRUST": "ПРАВОВАЯ ИНФОРМАЦИЯ И ДОВЕРИЕ",
  "TRANSPARENCY": "ПРОЗРАЧНОСТЬ",
  "COMMERCIAL TERMS": "КОММЕРЧЕСКИЕ УСЛОВИЯ",
  "CLINICAL SAFETY": "КЛИНИЧЕСКАЯ БЕЗОПАСНОСТЬ",
  "How Teta2 handles clinic applications, account information, patient records, OPG images and clinical workflow data.": "Как Teta2 обрабатывает заявки клиник, данные учетных записей, карты пациентов, изображения OPG и данные клинического рабочего процесса.",
  "1. Scope and roles": "1. Область действия и роли",
  "This policy applies to teta2.com, the clinic dashboard and the Teta2 access-request process. For clinic patient data, the clinic determines why the data is used and is normally the data controller; Teta2 processes that data to provide the contracted platform. For access requests, account administration, security and support, Teta2 determines the relevant processing purposes.": "Настоящая политика применяется к teta2.com, панели клиники и процессу подачи заявки на доступ к Teta2. В отношении данных пациентов клиника определяет цели их использования и, как правило, является оператором данных; Teta2 обрабатывает эти данные для предоставления согласованной платформы. Для заявок на доступ, администрирования учетных записей, безопасности и поддержки соответствующие цели обработки определяет Teta2.",
  "2. Information processed": "2. Обрабатываемая информация",
  "Teta2 processes only information provided through the service or generated by its operation.": "Teta2 обрабатывает только информацию, предоставленную через сервис или созданную в ходе его работы.",
  "Clinic application details: clinic name, country, city, address if supplied, website, contact person, role, email, phone, number of dentists and branches, and notes.": "Данные заявки клиники: название клиники, страна, город, при наличии — адрес и сайт, контактное лицо, должность, email, телефон, количество стоматологов и филиалов, а также примечания.",
  "Account and access data: username, email, role, clinic and branch permissions, authentication tokens and security events.": "Данные учетной записи и доступа: имя пользователя, email, роль, права клиники и филиалов, токены аутентификации и события безопасности.",
  "Patient and clinical data entered by an authorized clinic: identifiers, contact details, date of birth, sex, clinical records, OPG images, AI-assisted possible findings, clinician reviews, follow-up plans, messages and appointments.": "Данные пациентов и клинические данные, введенные уполномоченной клиникой: идентификаторы, контактные данные, дата рождения, пол, клинические записи, изображения OPG, возможные изменения, выявленные с поддержкой ИИ, результаты проверки врачом, планы последующего наблюдения, сообщения и приемы.",
  "Operational data: request identifiers, timestamps, delivery states, audit records and limited network/security metadata.": "Операционные данные: идентификаторы запросов, временные метки, статусы доставки, журналы аудита и ограниченные сетевые метаданные и метаданные безопасности.",
  "Payment administration data: payment reference, receipt notes, verification status and related correspondence. Teta2 does not currently collect payment-card data through an online checkout.": "Данные для администрирования платежей: идентификатор платежа, сведения о квитанции, статус проверки и связанная переписка. В настоящее время Teta2 не собирает данные платежных карт через онлайн-форму оплаты.",
  "3. Purposes and legal grounds": "3. Цели и правовые основания",
  "Information is used to review access requests, create and secure clinic workspaces, provide OPG and follow-up functions, deliver support, administer subscriptions and payments, prevent misuse, maintain auditability and comply with applicable law. Processing is based, as applicable, on performance of the service agreement, steps requested before entering that agreement, legitimate security and operational interests, legal obligations, and the clinic's lawful authority to process patient information.": "Информация используется для проверки заявок на доступ, создания и защиты рабочих пространств клиник, предоставления функций OPG и последующего наблюдения, поддержки, администрирования подписок и платежей, предотвращения злоупотреблений, обеспечения аудируемости и соблюдения применимого законодательства. В зависимости от ситуации обработка основывается на исполнении договора на оказание услуг, действиях, запрошенных до заключения договора, законных интересах в области безопасности и эксплуатации, юридических обязанностях и законных полномочиях клиники на обработку данных пациентов.",
  "4. Infrastructure and recipients": "4. Инфраструктура и получатели данных",
  "The production service uses infrastructure providers to host the frontend, application services and databases. The PostgreSQL database is hosted on AWS infrastructure. Authorized service providers receive only the information needed for hosting, email delivery, secure file storage or clinic-enabled messaging. When a clinic connects or uses WhatsApp, message and recipient information is also handled under the applicable WhatsApp/Meta terms. Teta2 does not sell patient or clinic personal data.": "Рабочая версия сервиса использует инфраструктурных поставщиков для размещения фронтенда, прикладных сервисов и баз данных. База данных PostgreSQL размещена в инфраструктуре AWS. Уполномоченные поставщики услуг получают только информацию, необходимую для хостинга, доставки электронной почты, защищенного хранения файлов или обмена сообщениями, подключенного клиникой. При подключении или использовании WhatsApp данные сообщений и получателей также обрабатываются в соответствии с применимыми условиями WhatsApp/Meta. Teta2 не продает персональные данные пациентов или клиник.",
  "5. Retention": "5. Срок хранения",
  "Data is retained while the clinic workspace is active and afterward where needed to preserve the clinic record, meet legal or security obligations, resolve disputes or support renewal. Subscription expiry locks access; it does not automatically delete clinic data. A clinic may request closure or deletion at the contact address below. Requests are assessed against the clinic's instructions, patient-safety needs and mandatory retention duties. Browser session tokens are removed when the browser session ends or the user signs out.": "Данные хранятся, пока рабочее пространство клиники активно, а затем — в той мере, в которой это необходимо для сохранения записей клиники, выполнения юридических или защитных обязательств, разрешения споров или продления доступа. Окончание подписки блокирует доступ, но не удаляет данные клиники автоматически. Клиника может запросить закрытие рабочего пространства или удаление данных по указанному ниже адресу. Запросы оцениваются с учетом указаний клиники, требований безопасности пациентов и обязательных сроков хранения. Токены браузерной сессии удаляются по завершении сессии или при выходе пользователя.",
  "6. Security": "6. Безопасность",
  "Teta2 uses access controls, tenant separation, protected transport, encrypted credential handling, audit records and restricted administrative access. No online service can promise absolute security. Clinics must keep credentials confidential, use authorized devices and report suspected access promptly.": "Teta2 использует контроль доступа, разделение данных клиник, защищенную передачу данных, шифрованную обработку учетных данных, журналы аудита и ограниченный административный доступ. Ни один онлайн-сервис не может гарантировать абсолютную безопасность. Клиники обязаны хранить учетные данные в тайне, использовать только авторизованные устройства и незамедлительно сообщать о подозрительном доступе.",
  "7. Rights and clinic responsibilities": "7. Права и обязанности клиники",
  "Under applicable Armenian data-protection law, individuals may request information about processing and, where applicable, access, correction, blocking or deletion. Patient requests should normally be directed to the treating clinic because the clinic controls the patient record. Teta2 will assist the clinic where required. Clinics must have a lawful basis and provide any required patient notice before uploading personal or clinical data.": "В соответствии с применимым законодательством Армении о защите данных физические лица могут запрашивать информацию об обработке и, где это применимо, доступ, исправление, блокировку или удаление. Запросы пациентов обычно следует направлять лечащей клинике, поскольку именно клиника контролирует карту пациента. При необходимости Teta2 окажет клинике содействие. До загрузки персональных или клинических данных клиника должна иметь законное основание и предоставить пациенту все требуемые уведомления.",
  "8. International processing and changes": "8. Международная обработка и изменения",
  "Service providers may process data outside the individual's country. Teta2 uses contractual and technical safeguards appropriate to the service and applicable law. Material policy changes will be posted on this page with a revised date.": "Поставщики услуг могут обрабатывать данные за пределами страны физического лица. Teta2 использует договорные и технические меры защиты, соответствующие сервису и применимому законодательству. Существенные изменения политики будут опубликованы на этой странице с обновленной датой.",

  "The rules governing access to and use of the Teta2 clinical software platform.": "Правила доступа к клинической программной платформе Teta2 и ее использования.",
  "1. Agreement and eligibility": "1. Согласие и правомочность",
  "By requesting access, paying for a subscription or using a clinic workspace, the clinic and its authorized users agree to these Terms. The person accepting must be legally able to act for the clinic. Teta2 is intended for professional dental-clinic use, not direct patient self-diagnosis or emergency care.": "Запрашивая доступ, оплачивая подписку или используя рабочее пространство клиники, клиника и ее уполномоченные пользователи соглашаются с настоящими Условиями. Лицо, принимающее их, должно иметь законное право действовать от имени клиники. Teta2 предназначен для профессионального использования стоматологическими клиниками, а не для самостоятельной диагностики пациентами или экстренной помощи.",
  "2. Access and subscription": "2. Доступ и подписка",
  "Public self-service activation is not currently available. Teta2 reviews each application, sends payment instructions when approved, verifies payment manually and then issues clinic credentials. The subscription period and price are those shown in the approved offer or payment instructions. The current standard activation flow provisions a fixed 30-day period. Renewal restores access to the same workspace unless otherwise agreed.": "Публичная самостоятельная активация в настоящее время недоступна. Teta2 проверяет каждую заявку, после одобрения отправляет инструкции по оплате, вручную подтверждает платеж и затем выдает клинике учетные данные. Срок и стоимость подписки указаны в одобренном предложении или инструкциях по оплате. Текущий стандартный процесс активации предусматривает фиксированный срок 30 дней. Продление восстанавливает доступ к тому же рабочему пространству, если стороны не договорились иначе.",
  "3. Clinical responsibility": "3. Клиническая ответственность",
  "Teta2 provides workflow software and AI-assisted possible findings. It does not provide a final diagnosis, treatment decision or substitute for examination by a qualified dentist. The clinic remains responsible for clinical review, patient consent, diagnosis, treatment, communications and compliance with professional rules.": "Teta2 предоставляет программные инструменты для клинического процесса и возможные изменения, выявленные с поддержкой ИИ. Сервис не устанавливает окончательный диагноз, не принимает решение о лечении и не заменяет осмотр квалифицированным стоматологом. Клиника остается ответственной за клиническую проверку, согласие пациента, диагноз, лечение, коммуникации и соблюдение профессиональных правил.",
  "4. Clinic obligations": "4. Обязанности клиники",
  "The clinic must provide accurate information, use patient data lawfully, limit access to authorized staff, protect credentials, review AI output before relying on it and keep its own legally required clinical records. The clinic must not upload data it is not authorized to process.": "Клиника обязана предоставлять точную информацию, законно использовать данные пациентов, ограничивать доступ уполномоченными сотрудниками, защищать учетные данные, проверять результат ИИ до того, как на него полагаться, и вести собственные клинические записи, требуемые законом. Клиника не должна загружать данные, которые она не уполномочена обрабатывать.",
  "5. Acceptable use": "5. Допустимое использование",
  "Users may not attempt unauthorized access, bypass tenant controls, probe or overload the service, reverse engineer protected components, upload malicious or unlawful content, use the system to make unsupervised clinical decisions, or use ordinary clinic access for automated bulk processing or resale. Fair-use limits may be applied to abnormal automation or API abuse.": "Пользователям запрещается пытаться получить несанкционированный доступ, обходить механизмы разделения данных клиник, тестировать на уязвимости или перегружать сервис, выполнять обратную разработку защищенных компонентов, загружать вредоносный или незаконный контент, использовать систему для клинических решений без контроля врача либо применять обычный доступ клиники для автоматизированной массовой обработки или перепродажи. При аномальной автоматизации или злоупотреблении API могут применяться ограничения добросовестного использования.",
  "6. Messaging and third parties": "6. Сообщения и третьи стороны",
  "Clinic-enabled WhatsApp messaging depends on the clinic's connected account and third-party availability. The clinic is responsible for lawful recipient consent, message content and communication timing. Third-party services remain subject to their own terms and may change independently of Teta2.": "Обмен сообщениями WhatsApp, подключенный клиникой, зависит от связанной учетной записи клиники и доступности стороннего сервиса. Клиника отвечает за законность согласия получателя, содержание сообщений и время коммуникации. Сторонние сервисы действуют на собственных условиях и могут изменяться независимо от Teta2.",
  "7. Availability, suspension and termination": "7. Доступность, приостановление и прекращение",
  "Teta2 may perform maintenance and cannot guarantee uninterrupted availability. Access may be suspended for non-payment, expired subscription, security risk, unlawful use or material breach. The clinic may stop using the service and request workspace closure by email. Data handling after expiry or closure follows the Privacy Policy and applicable law.": "Teta2 может проводить техническое обслуживание и не гарантирует непрерывную доступность. Доступ может быть приостановлен из-за неоплаты, окончания подписки, риска безопасности, незаконного использования или существенного нарушения. Клиника может прекратить использование сервиса и запросить закрытие рабочего пространства по электронной почте. Обработка данных после истечения срока или закрытия осуществляется в соответствии с Политикой конфиденциальности и применимым законодательством.",
  "8. Intellectual property and feedback": "8. Интеллектуальная собственность и обратная связь",
  "Teta2 and its software, interface and platform materials remain protected by applicable intellectual-property law. Clinics retain their rights in clinic and patient data. A subscription grants a limited, non-exclusive, non-transferable right to use the service during the active period. Feedback may be used to improve the platform without identifying patients or disclosing clinic-confidential information.": "Teta2, его программное обеспечение, интерфейс и материалы платформы защищаются применимым законодательством об интеллектуальной собственности. Клиники сохраняют права на данные клиники и пациентов. Подписка предоставляет ограниченное, неисключительное и непередаваемое право использовать сервис в течение активного периода. Обратная связь может использоваться для улучшения платформы без идентификации пациентов и раскрытия конфиденциальной информации клиники.",
  "9. Liability and law": "9. Ответственность и применимое право",
  "To the extent permitted by law, Teta2 is not liable for clinical decisions, missed diagnoses, treatment outcomes, third-party messaging failures or losses caused by unauthorized clinic use. Nothing in these Terms excludes liability that cannot lawfully be excluded. Disputes should first be raised at the support email for good-faith resolution.": "В пределах, допускаемых законом, Teta2 не несет ответственности за клинические решения, пропущенные диагнозы, результаты лечения, сбои сторонних сервисов сообщений или убытки, вызванные несанкционированным использованием клиникой. Ничто в настоящих Условиях не исключает ответственность, которую нельзя законно исключить. Для добросовестного урегулирования спор сначала следует направить на адрес поддержки.",

  "A precise list of what the current Teta2 frontend stores in your browser.": "Точный перечень того, что текущий фронтенд Teta2 хранит в вашем браузере.",
  "Teta2 currently uses no advertising or analytics cookies and no cookie-based tracking banner is required for those purposes.": "В настоящее время Teta2 не использует рекламные или аналитические cookie, поэтому баннер согласия на отслеживание для этих целей не требуется.",
  "1. Current storage": "1. Используемое хранилище",
  "The public frontend uses browser storage only for essential preferences and session operation.": "Публичный фронтенд использует хранилище браузера только для необходимых настроек и работы сессии.",
  "Language preference (`teta2-product-language` and compatibility key `teta2-v4-language`) is stored in localStorage so the selected language remains on the device.": "Выбор языка (`teta2-product-language` и совместимый ключ `teta2-v4-language`) хранится в localStorage, чтобы выбранный язык сохранялся на устройстве.",
  "The acknowledgement of the essential-storage notice (`teta2-storage-notice-v1`) is stored in localStorage.": "Подтверждение уведомления о необходимом хранилище (`teta2-storage-notice-v1`) хранится в localStorage.",
  "Clinic authentication tokens are stored in sessionStorage and are intended to last only for the active browser session.": "Токены аутентификации клиники хранятся в sessionStorage и предназначены только для текущей сессии браузера.",
  "Platform-administrator session data, where applicable, is also stored in sessionStorage.": "Данные сессии администратора платформы, где это применимо, также хранятся в sessionStorage.",
  "2. What is not used": "2. Что не используется",
  "The current Teta2 frontend does not include Google Analytics, Meta Pixel, PostHog, advertising cookies or cross-site behavioural tracking. Teta2 does not use the essential storage listed above to build advertising profiles.": "Текущий фронтенд Teta2 не включает Google Analytics, Meta Pixel, PostHog, рекламные cookie или межсайтовое отслеживание поведения. Teta2 не использует перечисленное выше необходимое хранилище для создания рекламных профилей.",
  "3. Your controls": "3. Ваши настройки",
  "You can clear localStorage and sessionStorage through your browser settings. Clearing language storage resets the language choice. Clearing session storage signs the user out. Blocking essential browser storage may prevent sign-in or preference persistence. If non-essential analytics or advertising technology is introduced later, this policy and the consent interface must be updated before that technology is activated.": "Вы можете очистить localStorage и sessionStorage в настройках браузера. Очистка языкового хранилища сбрасывает выбор языка, а очистка sessionStorage завершает вход пользователя. Блокировка необходимого хранилища браузера может помешать входу или сохранению настроек. Если позднее будут внедрены необязательные аналитические или рекламные технологии, эта политика и интерфейс согласия должны быть обновлены до их активации.",

  "How the current clinic subscription payment process actually works.": "Как фактически устроен текущий процесс оплаты подписки клиники.",
  "Teta2 does not currently operate an online card checkout or name Stripe, PayPal or another gateway as its payment processor.": "В настоящее время Teta2 не использует онлайн-оплату картой и не указывает Stripe, PayPal или другой платежный шлюз в качестве своего платежного оператора.",
  "1. Approved payment flow": "1. Утвержденный процесс оплаты",
  "A clinic first submits an access request. If approved, Teta2 sends the price, subscription period, recipient and payment instructions to the email supplied by the clinic. The clinic then sends its receipt or payment reference. Access is activated only after an administrator verifies payment. Never send money using details received from an unverified source; confirm unusual instructions through teta2support@gmail.com.": "Сначала клиника подает заявку на доступ. После одобрения Teta2 отправляет на указанный клиникой email стоимость, срок подписки, данные получателя и инструкции по оплате. Затем клиника отправляет квитанцию или идентификатор платежа. Доступ активируется только после проверки платежа администратором. Никогда не переводите деньги по реквизитам из непроверенного источника; необычные инструкции подтверждайте через teta2support@gmail.com.",
  "2. Price, currency and activation": "2. Цена, валюта и активация",
  "The binding amount and currency are those in the written payment instruction sent for that clinic. Prices displayed publicly are informational until the request is approved. The standard activation period is 30 days unless the written offer states otherwise. Failed, incomplete or unverifiable transfers do not activate access.": "Обязательными являются сумма и валюта, указанные в письменной инструкции по оплате, направленной данной клинике. Публично отображаемые цены носят информационный характер до одобрения заявки. Стандартный срок активации составляет 30 дней, если в письменном предложении не указано иное. Неуспешные, неполные или неподтверждаемые переводы не активируют доступ.",
  "3. Cancellations and refunds": "3. Отмена и возврат средств",
  "Because there is no automatic checkout, cancellation and refund eligibility must be stated in the written payment terms provided before payment. If those instructions do not address a refund situation, contact support promptly with the clinic name, payer, date, amount and payment reference. Teta2 will review the request against the agreed terms, whether access was activated or used, service-delivery evidence and any non-waivable rights under Armenian law. This page does not promise an automatic refund or remove rights that cannot legally be waived.": "Поскольку автоматическая онлайн-оплата отсутствует, условия отмены и право на возврат должны быть указаны в письменных платежных условиях, предоставленных до оплаты. Если эти инструкции не охватывают конкретную ситуацию возврата, оперативно свяжитесь с поддержкой, указав название клиники, плательщика, дату, сумму и идентификатор платежа. Teta2 рассмотрит запрос с учетом согласованных условий, факта активации или использования доступа, доказательств оказания услуги и неотчуждаемых прав по законодательству Армении. Эта страница не обещает автоматический возврат и не отменяет права, от которых нельзя законно отказаться.",
  "4. Expiry and renewal": "4. Окончание срока и продление",
  "At expiry, dashboard access is locked rather than the clinic workspace being automatically deleted. Renewal can restore the same clinic workspace and retained records, subject to the Privacy Policy, applicable law and any updated written offer.": "По окончании срока доступ к панели блокируется, но рабочее пространство клиники не удаляется автоматически. Продление может восстановить доступ к тому же рабочему пространству и сохраненным записям в соответствии с Политикой конфиденциальности, применимым законодательством и любым обновленным письменным предложением.",

  "The boundaries of Teta2's OPG analysis and follow-up assistance.": "Границы использования анализа OPG и помощи Teta2 в последующем наблюдении.",
  "Teta2 is clinical decision-support software. AI output is a possible finding—not a diagnosis.": "Teta2 — программное обеспечение для поддержки клинических решений. Результат ИИ — возможное изменение, а не диагноз.",
  "1. Qualified professional review required": "1. Требуется проверка квалифицированным специалистом",
  "Every image, highlight, label, report, priority or follow-up suggestion must be reviewed by a qualified dental professional together with the original OPG, examination, history and any additional imaging. A user must not treat model output as confirmed disease or absence of disease.": "Каждое изображение, выделение, обозначение, отчет, приоритет или рекомендация по последующему наблюдению должны быть проверены квалифицированным стоматологом вместе с исходным OPG, клиническим осмотром, анамнезом и любыми дополнительными снимками. Пользователь не должен считать результат модели подтвержденным заболеванием или доказательством отсутствия заболевания.",
  "2. Known limitations": "2. Известные ограничения",
  "AI can miss findings, mark normal anatomy, localize the wrong tooth or region, misread image artifacts and produce incomplete or incorrect text. Performance can vary with devices, positioning, exposure, anatomy, restorations, pathology and populations. Teta2 does not claim perfect or universally validated diagnostic accuracy.": "ИИ может пропускать изменения, ошибочно отмечать нормальные анатомические структуры, неверно локализовать зуб или область, неправильно интерпретировать артефакты изображения и формировать неполный или ошибочный текст. Результаты могут различаться в зависимости от оборудования, позиционирования, экспозиции, анатомии, реставраций, патологии и популяции. Teta2 не заявляет о безошибочной или универсально валидированной диагностической точности.",
  "3. Not for emergencies or autonomous care": "3. Не для экстренной или автономной медицинской помощи",
  "Teta2 is not an emergency service and must not delay urgent assessment. It must not autonomously diagnose, prescribe, select treatment or send clinical claims to a patient without the clinic's appropriate review and authority. The treating clinician remains responsible for the final record and care decision.": "Teta2 не является службой экстренной помощи и не должен задерживать срочную профессиональную оценку. Сервис не должен автономно диагностировать, назначать препараты, выбирать лечение или отправлять пациенту клинические утверждения без надлежащей проверки и полномочий клиники. Лечащий врач остается ответственным за итоговую запись и решение о лечении.",
  "4. Follow-up and messaging": "4. Последующее наблюдение и сообщения",
  "Priorities, schedules and messages support clinic workflow; they do not guarantee patient contact, attendance or outcome. Clinics must verify recipient identity, consent, message accuracy, urgency and suitable escalation. WhatsApp and other delivery services may fail or be unavailable independently of Teta2.": "Приоритеты, расписания и сообщения поддерживают рабочий процесс клиники, но не гарантируют контакт с пациентом, явку или клинический результат. Клиника должна проверять личность получателя, согласие, точность сообщения, срочность и необходимость эскалации. WhatsApp и другие сервисы доставки могут дать сбой или быть недоступны независимо от Teta2.",
};

const PAGE_HY: TextMap = {
  "Մեկ clinical loop՝ կառուցված պացիենտի, ոչ թե առանձին AI արդյունքի շուրջ։": "Մեկ կլինիկական շղթա՝ կառուցված պացիենտի, ոչ թե առանձին AI արդյունքի շուրջ։",
  "Teta2-ը կապում է panoramic image-ը, AI-assisted possible findings-ը, clinician review-ը, patient record-ը և follow-up-ը մեկ տեսանելի workflow-ում։": "Teta2-ը միավորում է պանորամիկ պատկերը, AI-աջակցվող հնարավոր փոփոխությունները, բժշկի վերանայումը, պացիենտի քարտը և հետագա վերահսկումը մեկ տեսանելի գործընթացում։",
  "OPG-ն մտնում է patient record": "OPG-ն ավելացվում է պացիենտի քարտին",
  "AI-assisted review": "AI-աջակցվող վերանայում",
  "Համակարգը surface է անում possible findings՝ բժշկի քննության համար։": "Համակարգը ցույց է տալիս հնարավոր փոփոխությունները՝ ատամնաբույժի գնահատման համար։",
  "Dentist-ը review է անում և context-ում confirm կամ reject է անում findings-ը։": "Ատամնաբույժը արդյունքները գնահատում է համատեքստում և հաստատում կամ մերժում դրանք։",
  "Follow-up-ը մնում է տեսանելի": "Հետագա վերահսկումը մնում է տեսանելի",
  "Problem/tooth-based follow-up-ը կապված է նույն patient record-ին։": "Խնդրին կամ առանձին ատամին վերաբերող հետագա վերահսկումը կապված է նույն պացիենտի քարտին։",
  "PATIENT WORKSPACE": "ՊԱՑԻԵՆՏԻ ԱՇԽԱՏԱՆՔԱՅԻՆ ՄԻՋԱՎԱՅՐ",
  "Օգտակար միավորը մեկ նկար չէ։ Դա պացիենտի clinical continuity-ն է։": "Արժեքը միայն մեկ պատկերում չէ․ կարևոր է պացիենտի կլինիկական շարունակականությունը։",
  "Workspace-ը միավորում է contact-ը, imaging-ը, review-ը, follow-up-ը և communication state-ը։": "Պացիենտի աշխատանքային միջավայրը միավորում է կոնտակտները, պատկերները, բժշկի վերանայումը, հետագա վերահսկումը և հաղորդակցության կարգավիճակը։",
  "Patient identity & contact": "Պացիենտի տվյալներ և կապ",
  "OPG history": "OPG պատմություն",
  "Possible findings": "Հնարավոր փոփոխություններ",
  "Review state": "Վերանայման կարգավիճակ",
  "Follow-up timing": "Հետագա վերահսկման ժամանակացույց",
  "Message state": "Հաղորդագրության կարգավիճակ",
  "Երեք operational visibility layer։": "Գործառնական տեսանելիության երեք մակարդակ։",
  "Product-ը կառուցված է գործողության ենթակա վիճակների շուրջ, ոչ decorative analytics-ի։": "Արտադրանքը կառուցված է տեսանելի և գործողության ենթակա կարգավիճակների, ոչ թե ձևական վերլուծական ցուցանիշների շուրջ։",
  "Clinical": "Կլինիկական",
  "Patient": "Պացիենտ",
  "Follow-up": "Հետագա վերահսկում",
  "Ֆոկուսը product որոշում է։": "Հստակ ֆոկուսը արտադրանքի գիտակցված որոշում է։",
  "OPG-centered clinical workflow": "OPG-ի շուրջ կառուցված կլինիկական գործընթաց",
  "AI-assisted findings dentist review-ի համար": "AI-աջակցվող հնարավոր փոփոխություններ՝ ատամնաբույժի վերանայման համար",
  "Patient-specific records": "Պացիենտին հատուկ քարտեր և պատմություն",
  "Clinical context-ին կապված follow-up": "Կլինիկական համատեքստին կապված հետագա վերահսկում",
  "Message և return state visibility": "Հաղորդագրությունների և վերադարձի կարգավիճակների տեսանելիություն",
  "Ոչ autonomous diagnosis": "Ոչ ինքնավար ախտորոշում",
  "Ոչ guaranteed detection": "Ոչ երաշխավորված հայտնաբերում",
  "Ոչ unpublished accuracy %": "Ոչ չհրապարակված ճշգրտության տոկոսներ",
  "Ոչ clinical exam replacement": "Ոչ կլինիկական զննման փոխարինում",
  "Ոչ ամբողջ hospital ERP/billing suite": "Ոչ հիվանդանոցի ամբողջական ERP կամ հաշվարկային համակարգ",
  "Լավագույն fit-ը՝ panoramic imaging օգտագործող կլինիկաներ, որոնք ուզում են ավելի հստակ follow-up loop։": "Լավագույն համապատասխանությունը՝ պանորամիկ պատկերներ օգտագործող կլինիկաներ, որոնք ցանկանում են ավելի հստակ հետագա վերահսկման շղթա։",
  "Teta2-ը առավել օգտակար է, երբ OPG, patient record և follow-up արդեն կան, բայց տարբեր tools/persons-ի միջև կտրված են։": "Teta2-ն առավել օգտակար է, երբ OPG-ն, պացիենտի քարտը և հետագա վերահսկումը արդեն կան, բայց բաժանված են տարբեր մարդկանց և գործիքների միջև։",
  "WORKFLOW, ՈՉ BLACK BOX": "ԳՈՐԾԸՆԹԱՑ, ՈՉ ԹԵ «ՍԵՎ ԱՐԿՂ»",
  "Upload-ից հետո տեղի ունեցողը նույնքան կարևոր է, որքան model output-ը։": "Վերբեռնումից հետո կատարվողը նույնքան կարևոր է, որքան մոդելի արդյունքը։",
  "Teta2-ը տեսանելի է պահում՝ ով է review արել, ինչ follow-up կա, outreach-ը ուղարկվել է թե ոչ և պացիենտը վերադարձել է թե ոչ։": "Teta2-ը հստակ ցույց է տալիս՝ ով է վերանայել արդյունքը, ինչ հետագա վերահսկում է ստեղծված, ուղարկվել է արդյոք հաղորդագրությունը և վերադարձել է արդյոք պացիենտը։",
  "Create patient": "Ստեղծել պացիենտ",
  "Upload OPG": "Վերբեռնել OPG",
  "AI-assisted analysis": "AI-աջակցվող վերլուծություն",
  "Clinical review": "Կլինիկական վերանայում",
  "Keep the record": "Պահպանել քարտում",
  "Set follow-up": "Սահմանել հետագա վերահսկումը",
  "Send outreach": "Կապ հաստատել պացիենտի հետ",
  "Track return": "Հետևել վերադարձին",
  "STATE MACHINE": "ԿԱՐԳԱՎԻՃԱԿՆԵՐԻ ՇՂԹԱ",
  "Workflow-ը explicit states-ի շուրջ է, ոչ assumptions-ի։": "Գործընթացը կառուցված է հստակ կարգավիճակների, ոչ թե ենթադրությունների շուրջ։",
  "State-ը ցույց է տալիս՝ ինչ է արդեն եղել, ոչ թե ինչ պետք է ենթադրել հաջորդը։": "Կարգավիճակը ցույց է տալիս՝ ինչ է արդեն տեղի ունեցել, և չի ներկայացնում հաջորդ քայլը որպես կատարված։",
  "ԵՐԵՔ RESPONSIBILITY GATE": "ՊԱՏԱՍԽԱՆԱՏՎՈՒԹՅԱՆ ԵՐԵՔ ՓՈՒԼ",
  "Automation-ը տեղափոխում է ինֆորմացիան։ Responsibility-ն մնում է տեսանելի։": "Ավտոմատացումը փոխանցում է տեղեկությունը, իսկ պատասխանատվությունը մնում է հստակ տեսանելի։",
  "ԵՐԲ FLOW-Ը ՉԻ ԱՎԱՐՏՎՈՒՄ": "ԵՐԲ ԳՈՐԾԸՆԹԱՑԸ ՉԻ ԱՎԱՐՏՎՈՒՄ",
  "Համակարգը պետք է ցույց տա unfinished work-ը։": "Համակարգը պետք է տեսանելի պահի չավարտված աշխատանքը։",
  "AUTOMATION BOUNDARY": "ԱՎՏՈՄԱՏԱՑՄԱՆ ՍԱՀՄԱՆՆԵՐ",
  "Չորս բան, որ Teta2-ը ինքնուրույն չի ենթադրում։": "Չորս բան, որոնք Teta2-ը ինքնուրույն չի ենթադրում։",
  "CLINIC SUBSCRIPTION": "ԿԼԻՆԻԿԱՅԻ ԲԱԺԱՆՈՐԴԱԳՐՈՒԹՅՈՒՆ",
  "Երկու շուկա։ Մեկ պարզ monthly subscription model։": "Երկու շուկա։ Մեկ պարզ ամսական բաժանորդագրություն։",
  "Գինը մեկ clinic-ի համար է ամսական։ Funding Plan-ը սահմանափակ launch price է յուրաքանչյուր շուկայում առաջին 50 clinics-ի համար։ Availability-ն հաստատվում է access review-ի ժամանակ։": "Գինը նշված է մեկ կլինիկայի համար՝ ամսական։ Մեկնարկային արտոնյալ սակագինը սահմանափակ է յուրաքանչյուր շուկայում առաջին 50 կլինիկաներով, իսկ հասանելիությունը հաստատվում է մուտքի հայտի ստուգման ընթացքում։",
  "Առաջին 50 clinics": "Առաջին 50 կլինիկաները",
  "Launch price առաջին 50 clinics-ի համար — ոչ stripped-down product tier։": "Մեկնարկային գին առաջին 50 կլինիկաների համար՝ առանց գործառույթների կրճատման։",
  "Վճարվող արժեքը հենց workflow-ն է։": "Վճարվող արժեքը հենց ամբողջական աշխատանքային գործընթացն է։",
  "Normal clinical use-ի համար per-OPG counter չկա։": "Սովորական կլինիկական օգտագործման դեպքում յուրաքանչյուր OPG-ի առանձին հաշվարկ չկա։",
  "ACCESS PROCESS": "ՄՈՒՏՔԻ ԳՈՐԾԸՆԹԱՑ",
  "Clinic access-ը provision է արվում վերահսկված ձևով։": "Կլինիկայի մուտքն ակտիվացվում է վերահսկվող գործընթացով։",
  "CLINICAL SAFETY": "ԿԼԻՆԻԿԱԿԱՆ ԱՆՎՏԱՆԳՈՒԹՅՈՒՆ",
  "Safety-ն սկսվում է այն claims-ից, որոնք product-ը չի անում։": "Անվտանգությունը սկսվում է այն պնդումներից, որոնք արտադրանքը չի անում։",
  "Teta2-ը ներկայացնում է AI-assisted possible findings dentist examination-ի համար։ Model output-ը definitive diagnosis չի ներկայացվում և unpublished accuracy claim չի արվում։": "Teta2-ը ներկայացնում է AI-աջակցվող հնարավոր փոփոխություններ՝ ատամնաբույժի գնահատման համար։ Մոդելի արդյունքը չի ներկայացվում որպես վերջնական ախտորոշում, և չվավերացված ճշգրտության ցուցանիշներ չեն հրապարակվում։",
  "CLAIMS BOUNDARY": "ՊՆԴՈՒՄՆԵՐԻ ՍԱՀՄԱՆՆԵՐ",
  "Responsible language-ը decision boundary-ն հստակ է պահում։": "Պատասխանատու ձևակերպումները հստակ պահում են որոշման սահմանը։",
  "HUMAN IN THE LOOP": "ՄԱՍՆԱԳԵՏԸ ՄՆՈՒՄ Է ԳՈՐԾԸՆԹԱՑՈՒՄ",
  "AI-ը surface է անում ինֆորմացիան։ Decision gate-ը clinician-ինն է։": "AI-ը ներկայացնում է տեղեկությունը, իսկ որոշման վերջնական փուլը մնում է բժշկին։",
  "IMAGING CONTEXT": "ՊԱՏԿԵՐԱՅԻՆ ՀԱՄԱՏԵՔՍՏ",
  "OPG-ն clinical evidence է, ոչ ամբողջ clinical examination-ը։": "OPG-ն կլինիկական տեղեկատվության մի մասն է, ոչ ամբողջ կլինիկական զննումը։",
  "OPERATIONAL HONESTY": "ԳՈՐԾԱՌՆԱԿԱՆ ԹԱՓԱՆՑԻԿՈՒԹՅՈՒՆ",
  "Interface-ը տարբերակում է այն, ինչ եղել է, նրանից, ինչ դեռ սպասվում է։": "Միջերեսը հստակ տարբերակում է արդեն կատարվածը դեռ սպասվող քայլերից։",
  "Ֆոկուսավորված dental AI նախագիծ՝ կառուցվող Երևանում։": "Երևանում ստեղծվող՝ հստակ ուղղվածություն ունեցող ատամնաբուժական AI նախագիծ։",
  "Teta2-ը կառուցվում է մեկ նեղ operational խնդրի շուրջ՝ OPG review-ը կապել patient record-ի և visible follow-up workflow-ի հետ։ Site-ը ներկայացնում է այն որպես pre-incorporation software project, ոչ regulatory approval claim։": "Teta2-ը ստեղծվում է մեկ հստակ գործառնական խնդրի շուրջ՝ OPG-ի վերանայումը կապել պացիենտի քարտի և տեսանելի հետագա վերահսկման գործընթացի հետ։ Կայքը նախագիծը ներկայացնում է որպես դեռևս չգրանցված ծրագրային նախաձեռնություն, ոչ թե կարգավորիչ հաստատում ստացած բժշկական համակարգ։",
  "Radiograph-ը չպետք է դառնա isolated AI result։ Այն պետք է կապված մնա clinician-ի, patient-ի և next action-ի հետ։": "Ռենտգեն պատկերը չպետք է դառնա մեկուսացված AI արդյունք։ Այն պետք է կապված մնա բժշկի, պացիենտի և հաջորդ գործողության հետ։",
  "Roles-ը դիտավորյալ narrow/factual են։ Public links-ը տրված են այնտեղ, որտեղ կան։": "Դերերը ներկայացված են հստակ և փաստացի ձևով։ Հանրային աղբյուրների հղումները տրված են այնտեղ, որտեղ դրանք առկա են։",
  "Founder · Teta2": "Հիմնադիր · Teta2",
  "Co-founder · Technical / AI model fine-tuning": "Համահիմնադիր · Տեխնիկական աշխատանք / AI մոդելի ճշգրտում",
  "Public profile": "Հանրային պրոֆիլ",
  "Public source": "Հանրային աղբյուր",
  "ԻՆՉՊԵՍ Է ԿԱՌՈՒՑՎՈՒՄ PROJECT-Ը": "ԻՆՉՊԵՍ Է ԿԱՌՈՒՑՎՈՒՄ ՆԱԽԱԳԻԾԸ",
  "Narrow scope, visible states և պաշտպանելի claims։": "Հստակ սահմաններ, տեսանելի կարգավիճակներ և հիմնավորվող պնդումներ։",
  "Clinic access-ի, product հարցերի, technical discussion-ի կամ partnership-ի համար ընտրեք հարմար channel-ը։": "Կլինիկայի մուտքի, արտադրանքի հարցերի, տեխնիկական քննարկման կամ գործընկերության համար ընտրեք ձեզ հարմար կապի միջոցը։",
};

const PAGE_RU: TextMap = {
  "Один clinical loop вокруг пациента, а не вокруг отдельного AI-результата.": "Один клинический цикл вокруг пациента, а не вокруг отдельного результата ИИ.",
  "Teta2 связывает панорамный снимок, AI-assisted possible findings, review врача, patient record и follow-up в один видимый workflow.": "Teta2 объединяет панорамный снимок, возможные изменения с поддержкой ИИ, проверку врачом, карту пациента и последующее наблюдение в один прозрачный рабочий процесс.",
  "OPG входит в карту пациента": "OPG добавляется в карту пациента",
  "AI-assisted review": "Проверка с поддержкой ИИ",
  "Система показывает possible findings для оценки стоматологом.": "Система показывает возможные изменения для оценки стоматологом.",
  "Стоматолог оценивает finding в контексте и подтверждает или отклоняет его.": "Стоматолог оценивает результат в клиническом контексте и подтверждает или отклоняет его.",
  "Follow-up остается видимым": "Последующее наблюдение остается видимым",
  "Problem/tooth-based follow-up связан с тем же patient record.": "Последующее наблюдение по проблеме или конкретному зубу связано с той же картой пациента.",
  "PATIENT WORKSPACE": "РАБОЧЕЕ ПРОСТРАНСТВО ПАЦИЕНТА",
  "Полезная единица — не один снимок, а клиническая непрерывность пациента.": "Ценность — не в одном снимке, а в непрерывности клинического наблюдения пациента.",
  "Workspace связывает контакт, imaging, review, follow-up и communication state.": "Рабочее пространство объединяет контактные данные, изображения, проверку врачом, последующее наблюдение и статус коммуникации.",
  "Patient identity & contact": "Данные пациента и контакты",
  "OPG history": "История OPG",
  "Possible findings": "Возможные изменения",
  "Review state": "Статус проверки",
  "Follow-up timing": "Сроки наблюдения",
  "Message state": "Статус сообщений",
  "Три уровня operational visibility.": "Три уровня операционной прозрачности.",
  "Продукт строится вокруг наблюдаемых состояний, а не декоративной аналитики.": "Продукт строится вокруг понятных состояний, по которым можно действовать, а не вокруг декоративной аналитики.",
  "Clinical": "Клинический уровень",
  "Patient": "Пациент",
  "Follow-up": "Наблюдение",
  "ОСОЗНАННЫЙ SCOPE": "ОСОЗНАННЫЕ ГРАНИЦЫ",
  "Фокус — продуктовое решение.": "Узкий фокус — осознанное продуктовое решение.",
  "OPG-centered clinical workflow": "Клинический процесс вокруг OPG",
  "AI-assisted findings для review врача": "Возможные изменения с поддержкой ИИ для проверки врачом",
  "Patient-specific records": "Карты и история конкретного пациента",
  "Follow-up в clinical context": "Последующее наблюдение в клиническом контексте",
  "Message/return visibility": "Видимые статусы сообщений и возвращения пациента",
  "Не autonomous diagnosis": "Не автономная диагностика",
  "Не guaranteed detection": "Не гарантированное выявление",
  "Не unpublished accuracy %": "Не неопубликованные проценты точности",
  "Не замена clinical examination": "Не замена клинического осмотра",
  "Не полный hospital ERP/billing suite": "Не полноценная больничная ERP или биллинговая система",
  "Лучший fit — клиники с panoramic imaging, которым нужен более четкий follow-up loop.": "Лучше всего подходит клиникам, использующим панорамные снимки и нуждающимся в более четком цикле последующего наблюдения.",
  "Teta2 полезен, когда OPG, patient record и follow-up уже существуют, но разделены между людьми и инструментами.": "Teta2 особенно полезен, когда OPG, карта пациента и последующее наблюдение уже существуют, но разрознены между сотрудниками и инструментами.",
  "WORKFLOW, А НЕ BLACK BOX": "РАБОЧИЙ ПРОЦЕСС, А НЕ «ЧЕРНЫЙ ЯЩИК»",
  "То, что происходит после upload, так же важно, как model output.": "То, что происходит после загрузки, так же важно, как результат модели.",
  "Teta2 делает видимыми review, follow-up, outreach и return пациента.": "Teta2 делает видимыми проверку врачом, последующее наблюдение, связь с пациентом и его возвращение в клинику.",
  "Create patient": "Создать пациента",
  "Upload OPG": "Загрузить OPG",
  "AI-assisted analysis": "Анализ с поддержкой ИИ",
  "Clinical review": "Клиническая проверка",
  "Keep the record": "Сохранить в карте",
  "Set follow-up": "Назначить наблюдение",
  "Send outreach": "Связаться с пациентом",
  "Track return": "Отслеживать возвращение",
  "STATE MACHINE": "ЦЕПОЧКА СТАТУСОВ",
  "Workflow строится на explicit states, а не предположениях.": "Рабочий процесс строится на явных статусах, а не на предположениях.",
  "State показывает, что уже произошло, и не делает вид, что следующий шаг завершен.": "Статус показывает, что уже произошло, и не выдает следующий шаг за выполненный.",
  "ТРИ RESPONSIBILITY GATE": "ТРИ УРОВНЯ ОТВЕТСТВЕННОСТИ",
  "Automation переносит информацию. Responsibility остается видимой.": "Автоматизация передает информацию, а ответственность остается четко обозначенной.",
  "ЕСЛИ FLOW НЕ ЗАВЕРШЕН": "ЕСЛИ ПРОЦЕСС НЕ ЗАВЕРШЕН",
  "Система должна показывать unfinished work.": "Система должна показывать незавершенную работу.",
  "AUTOMATION BOUNDARY": "ГРАНИЦЫ АВТОМАТИЗАЦИИ",
  "CLINIC SUBSCRIPTION": "ПОДПИСКА ДЛЯ КЛИНИКИ",
  "Два рынка. Одна понятная monthly subscription model.": "Два рынка. Одна понятная модель ежемесячной подписки.",
  "Цена указана за одну clinic в месяц. Funding Plan — ограниченная launch price для первых 50 clinics в каждом рынке; availability подтверждается при access review.": "Цена указана за одну клинику в месяц. Льготный стартовый тариф доступен первым 50 клиникам на каждом рынке; его доступность подтверждается при проверке заявки.",
  "Первые 50 clinics": "Первые 50 клиник",
  "Launch price для первых 50 clinics — не урезанный product tier.": "Стартовая цена для первых 50 клиник — без урезания функций продукта.",
  "Оплачивается сам рабочий workflow.": "Клиника оплачивает полноценный рабочий процесс.",
  "Для normal clinical use нет per-OPG counter.": "Для обычного клинического использования нет оплаты за каждый OPG.",
  "ACCESS PROCESS": "ПРОЦЕСС ДОСТУПА",
  "Clinic access provisioned намеренно.": "Доступ клиники активируется контролируемым образом.",
  "CLINICAL SAFETY": "КЛИНИЧЕСКАЯ БЕЗОПАСНОСТЬ",
  "Safety начинается с claims, которые продукт отказывается делать.": "Безопасность начинается с утверждений, от которых продукт сознательно отказывается.",
  "Teta2 показывает AI-assisted possible findings для dentist examination. Model output не выдается за definitive diagnosis, unpublished accuracy claim не публикуется.": "Teta2 показывает возможные изменения с поддержкой ИИ для оценки стоматологом. Результат модели не выдается за окончательный диагноз, а неподтвержденные показатели точности не публикуются.",
  "CLAIMS BOUNDARY": "ГРАНИЦЫ УТВЕРЖДЕНИЙ",
  "Responsible language сохраняет ясную границу решения.": "Ответственные формулировки сохраняют четкую границу принятия решения.",
  "HUMAN IN THE LOOP": "СПЕЦИАЛИСТ ОСТАЕТСЯ В ПРОЦЕССЕ",
  "AI показывает информацию. Decision gate остается за clinician.": "ИИ показывает информацию, а окончательное решение остается за врачом.",
  "IMAGING CONTEXT": "КОНТЕКСТ ВИЗУАЛИЗАЦИИ",
  "OPG — clinical evidence, но не весь clinical examination.": "OPG — часть клинической информации, но не весь клинический осмотр.",
  "OPERATIONAL HONESTY": "ОПЕРАЦИОННАЯ ПРОЗРАЧНОСТЬ",
  "Фокусированный dental AI проект, создаваемый в Ереване.": "Специализированный проект стоматологического ИИ, создаваемый в Ереване.",
  "Teta2 строится вокруг одной operational задачи: связать OPG review с patient record и visible follow-up workflow. Сайт представляет проект как pre-incorporation software project, а не regulatory approval claim.": "Teta2 решает одну конкретную операционную задачу: связывает проверку OPG с картой пациента и прозрачным процессом последующего наблюдения. Сайт представляет Teta2 как программный проект до регистрации компании, а не как медицинскую систему с заявленным регуляторным одобрением.",
  "Radiograph не должен становиться isolated AI result. Он должен оставаться связанным с clinician, patient и next action.": "Рентгеновский снимок не должен превращаться в изолированный результат ИИ. Он должен оставаться связанным с врачом, пациентом и следующим действием.",
  "Roles намеренно описаны узко и фактически. Public-source links добавлены там, где они есть.": "Роли описаны узко и фактически. Ссылки на публичные источники приведены там, где они доступны.",
  "Founder · Teta2": "Основатель · Teta2",
  "Co-founder · Technical / AI model fine-tuning": "Сооснователь · Техническая работа / донастройка модели ИИ",
  "Public profile": "Публичный профиль",
  "Public source": "Публичный источник",
  "КАК СТРОИТСЯ ПРОЕКТ": "КАК СОЗДАЕТСЯ ПРОЕКТ",
  "Narrow scope, visible states и claims, которые можно защитить.": "Четкие границы, видимые статусы и обоснованные утверждения.",
  "Для clinic access, product вопросов, technical discussion или partnerships используйте удобный канал.": "По вопросам доступа для клиники, продукта, технических деталей или партнерства используйте удобный способ связи.",
};

const PUBLIC_RULES_HY: Array<[RegExp, string]> = [
  [/follow-up/gi, "հետագա վերահսկում"],
  [/workspace/gi, "աշխատանքային միջավայր"],
  [/workflow/gi, "գործընթաց"],
  [/AI-assisted/gi, "AI-աջակցվող"],
  [/patient record/gi, "պացիենտի քարտ"],
  [/possible findings/gi, "հնարավոր փոփոխություններ"],
  [/possible finding/gi, "հնարավոր փոփոխություն"],
  [/clinician review/gi, "բժշկի վերանայում"],
  [/clinical examination/gi, "կլինիկական զննում"],
  [/model output/gi, "մոդելի արդյունք"],
  [/outreach/gi, "պացիենտի հետ կապ"],
  [/subscription/gi, "բաժանորդագրություն"],
  [/launch price/gi, "մեկնարկային գին"],
  [/access review/gi, "մուտքի հայտի ստուգում"],
  [/clinical/gi, "կլինիկական"],
];

const PUBLIC_RULES_RU: Array<[RegExp, string]> = [
  [/follow-up/gi, "последующее наблюдение"],
  [/workspace/gi, "рабочее пространство"],
  [/workflow/gi, "рабочий процесс"],
  [/AI-assisted/gi, "с поддержкой ИИ"],
  [/patient record/gi, "карта пациента"],
  [/possible findings/gi, "возможные изменения"],
  [/possible finding/gi, "возможное изменение"],
  [/clinician review/gi, "проверка врачом"],
  [/clinical examination/gi, "клинический осмотр"],
  [/model output/gi, "результат модели"],
  [/outreach/gi, "связь с пациентом"],
  [/subscription/gi, "подписка"],
  [/launch price/gi, "стартовая цена"],
  [/access review/gi, "проверка заявки"],
];

const originalText = new WeakMap<Text, string>();
const lastText = new WeakMap<Text, string>();
const originalAttribute = new WeakMap<Element, Map<string, string>>();
const lastAttribute = new WeakMap<Element, Map<string, string>>();

function currentLanguage(): Lang {
  const stored = localStorage.getItem("teta2-product-language") ?? localStorage.getItem("teta2-v4-language");
  if (stored === "hy" || stored === "ru") return stored;
  if (stored === "en") return "en";
  const html = document.documentElement.lang.toLowerCase();
  if (html.startsWith("hy")) return "hy";
  if (html.startsWith("ru")) return "ru";
  return "en";
}

function isPublicStatic(element: Element | null): boolean {
  return Boolean(element?.closest(".deck2, .product-public, .product-auth-shell, .pav2-access-page, .t2-legal-page, .t2-footer, .t2-navbar, .t2-storage-notice, .homepage-evidence-root"));
}

function isStatusElement(element: Element | null): boolean {
  return Boolean(element?.closest(".clinical-pill, .case-status, .clinic-status, .conversation-appointment > b, .enhanced-thread article > small"));
}

function statusTranslation(value: string, lang: Lang): string | null {
  if (lang === "hy") return STATUS_HY[value] ?? null;
  if (lang === "ru") return STATUS_RU[value] ?? null;
  return EN[value] ?? null;
}

function translateDynamic(value: string, lang: Lang): string | null {
  let match = value.match(/^Analysis status:\s*(.+)$/);
  if (match) return lang === "hy" ? `Վերլուծության կարգավիճակ՝ ${STATUS_HY[match[1]] ?? match[1]}` : lang === "ru" ? `Статус анализа: ${STATUS_RU[match[1]] ?? match[1]}` : value;

  match = value.match(/^(\d+) pathological\/red teeth can enter the plan\. Confidence affects priority and review guidance, not eligibility\.$/);
  if (match) return lang === "hy" ? `${match[1]} պաթոլոգիական ատամ կարող է ընդգրկվել պլանում։ Վստահության միավորը ազդում է առաջնահերթության և վերանայման առաջարկի վրա, ոչ թե ընդգրկվելու իրավասության։` : lang === "ru" ? `${match[1]} зубов с возможными патологическими изменениями можно включить в план. Уверенность модели влияет на приоритет и рекомендацию проверки, но не на право включения.` : value;
  match = value.match(/^(\d+) pathological\/red tooth can enter the plan\. Confidence affects priority and review guidance, not eligibility\.$/);
  if (match) return lang === "hy" ? `${match[1]} պաթոլոգիական ատամ կարող է ընդգրկվել պլանում։ Վստահության միավորը ազդում է առաջնահերթության և վերանայման առաջարկի վրա, ոչ թե ընդգրկվելու իրավասության։` : lang === "ru" ? `${match[1]} зуб с возможным патологическим изменением можно включить в план. Уверенность модели влияет на приоритет и рекомендацию проверки, но не на право включения.` : value;

  match = value.match(/^Review recommended for (\d+) teeth?, but generation is available now\.$/);
  if (match) return lang === "hy" ? `Խորհուրդ է տրվում վերանայել ${match[1]} ատամ, սակայն պլանը կարելի է ստեղծել արդեն հիմա։` : lang === "ru" ? `Рекомендуется проверить ${match[1]} зуб(а), но план можно создать уже сейчас.` : value;

  match = value.match(/^Sequential follow-up plan generated for (\d+) pathological teeth?\.$/);
  if (match) return lang === "hy" ? `Ստեղծվել է հերթական հետագա վերահսկման պլան՝ ${match[1]} պաթոլոգիական ատամի համար։` : lang === "ru" ? `Создан последовательный план наблюдения для ${match[1]} зуб(а) с патологическими изменениями.` : value;

  match = value.match(/^Generated a sequential plan for (\d+) pathological tooth findings?\.$/);
  if (match) return lang === "hy" ? `Ստեղծվել է հերթական պլան՝ ${match[1]} պաթոլոգիական ատամի համար։` : lang === "ru" ? `Создан последовательный план для ${match[1]} зуб(а) с патологическими изменениями.` : value;

  match = value.match(/^Review is recommended, not required\. (\d+)\/(\d+) currently clinician-confirmed\.$/);
  if (match) return lang === "hy" ? `Բժշկի վերանայումը խորհուրդ է տրվում, բայց պարտադիր չէ։ Ներկայում բժշկի կողմից հաստատված է ${match[1]}/${match[2]}։` : lang === "ru" ? `Проверка врачом рекомендуется, но не обязательна. Сейчас врачом подтверждено ${match[1]}/${match[2]}.` : value;

  match = value.match(/^Saved tooth (\d+)\.$/);
  if (match) return lang === "hy" ? `Պահպանվել է ${match[1]} ատամի պլանը։` : lang === "ru" ? `План по зубу ${match[1]} сохранен.` : value;

  match = value.match(/^Tooth (\d+) · (.+)$/);
  if (match) return lang === "hy" ? `Ատամ ${match[1]} · ${HY[match[2]] ?? match[2].replace(/ · reviewed$/, " · վերանայված")}` : lang === "ru" ? `Зуб ${match[1]} · ${RU[match[2]] ?? match[2].replace(/ · reviewed$/, " · проверено")}` : value;

  match = value.match(/^Sender: (.+)\. This single clinic account is used for authorized patient follow-up\.$/);
  if (match) return lang === "hy" ? `Ուղարկող՝ ${match[1]}։ Այս մեկ կլինիկական հաշիվն օգտագործվում է լիազորված պացիենտների հետագա վերահսկման համար։` : lang === "ru" ? `Отправитель: ${match[1]}. Эта единая учетная запись клиники используется для разрешенного последующего наблюдения пациентов.` : value;

  match = value.match(/^Next: (.+)$/);
  if (match) return lang === "hy" ? `Հաջորդը՝ ${localizeEnglishDate(match[1], lang)}` : lang === "ru" ? `Далее: ${localizeEnglishDate(match[1], lang)}` : value;

  match = value.match(/^(\d+) teeth$/);
  if (match) return lang === "hy" ? `${match[1]} ատամ` : lang === "ru" ? `${match[1]} зуб(а)` : value;

  match = value.match(/^First WhatsApp outreach rescheduled to (.+)\.$/);
  if (match) return lang === "hy" ? `WhatsApp-ի առաջին հաղորդագրության ժամը փոխվել է՝ ${localizeEnglishDate(match[1], lang)}։` : lang === "ru" ? `Время первого сообщения WhatsApp изменено: ${localizeEnglishDate(match[1], lang)}.` : value;

  match = value.match(/^Outcome recorded (.+)$/);
  if (match) return lang === "hy" ? `Արդյունքը գրանցվել է՝ ${localizeEnglishDate(match[1], lang)}` : lang === "ru" ? `Результат зафиксирован: ${localizeEnglishDate(match[1], lang)}` : value;

  match = value.match(/^Tooth (\d+)$/);
  if (match) return lang === "hy" ? `Ատամ ${match[1]}` : lang === "ru" ? `Зуб ${match[1]}` : value;

  return null;
}

const MONTHS: Record<string, number> = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5, Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 };

function localizeEnglishDate(value: string, lang: Lang): string {
  if (lang === "en") return value;
  const match = value.match(/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+(\d{4})(?:,\s+(\d{1,2}):(\d{2})\s+(AM|PM))?$/);
  if (!match) return value;
  const month = MONTHS[match[1]];
  const day = Number(match[2]);
  const year = Number(match[3]);
  let hour = match[4] ? Number(match[4]) : 0;
  const minute = match[5] ? Number(match[5]) : 0;
  if (match[6] === "PM" && hour !== 12) hour += 12;
  if (match[6] === "AM" && hour === 12) hour = 0;
  const date = new Date(Date.UTC(year, month, day, hour, minute));
  return new Intl.DateTimeFormat(lang === "hy" ? "hy-AM" : "ru-RU", {
    timeZone: "UTC",
    year: "numeric",
    month: "short",
    day: "numeric",
    ...(match[4] ? { hour: "2-digit", minute: "2-digit", hourCycle: "h23" as const } : {}),
  }).format(date);
}

function translateValue(source: string, lang: Lang, element: Element | null): string {
  const trimmed = source.trim();
  if (!trimmed) return source;
  const exact = lang === "hy" ? HY : lang === "ru" ? RU : EN;
  const legal = lang === "hy" ? LEGAL_HY : lang === "ru" ? LEGAL_RU : EN;
  const page = lang === "hy" ? PAGE_HY : lang === "ru" ? PAGE_RU : EN;

  let translated = exact[trimmed] ?? legal[trimmed] ?? page[trimmed] ?? translateDynamic(trimmed, lang) ?? trimmed;

  if (isStatusElement(element)) {
    translated = statusTranslation(trimmed, lang) ?? translated;
  }

  if (lang !== "en" && isPublicStatic(element)) {
    const rules = lang === "hy" ? PUBLIC_RULES_HY : PUBLIC_RULES_RU;
    for (const [pattern, replacement] of rules) translated = translated.replace(pattern, replacement);
  }

  if (lang !== "en" && element?.closest(".followup-case-shell, .care-enhancer-host")) {
    translated = translated.replace(/\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}(?:,\s+\d{1,2}:\d{2}\s+(?:AM|PM))?\b/g, (date) => localizeEnglishDate(date, lang));
  }

  if (translated === trimmed) return source;
  const leading = source.slice(0, source.indexOf(trimmed));
  const trailing = source.slice(source.indexOf(trimmed) + trimmed.length);
  return `${leading}${translated}${trailing}`;
}

function translateTextNode(node: Text, lang: Lang): void {
  const current = node.nodeValue ?? "";
  const previousOutput = lastText.get(node);
  if (!originalText.has(node) || (previousOutput !== undefined && current !== previousOutput)) {
    originalText.set(node, current);
  }
  const source = originalText.get(node) ?? current;
  const output = translateValue(source, lang, node.parentElement);
  if (current !== output) node.nodeValue = output;
  lastText.set(node, output);
}

function translateAttribute(element: Element, attribute: "placeholder" | "aria-label" | "title", lang: Lang): void {
  const current = element.getAttribute(attribute);
  if (current == null) return;
  let originals = originalAttribute.get(element);
  if (!originals) { originals = new Map(); originalAttribute.set(element, originals); }
  let outputs = lastAttribute.get(element);
  if (!outputs) { outputs = new Map(); lastAttribute.set(element, outputs); }
  const last = outputs.get(attribute);
  if (!originals.has(attribute) || (last !== undefined && current !== last)) originals.set(attribute, current);
  const source = originals.get(attribute) ?? current;
  const output = translateValue(source, lang, element);
  if (current !== output) element.setAttribute(attribute, output);
  outputs.set(attribute, output);
}

function translateTree(root: Node, lang: Lang): void {
  if (root.nodeType === Node.TEXT_NODE) {
    translateTextNode(root as Text, lang);
    return;
  }
  if (!(root instanceof Element) && root !== document.body) return;

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    translateTextNode(node as Text, lang);
    node = walker.nextNode();
  }

  const elements: Element[] = [];
  if (root instanceof Element) elements.push(root);
  if (root instanceof Element || root === document.body) elements.push(...Array.from((root as Element | HTMLElement).querySelectorAll?.("[placeholder], [aria-label], [title]") ?? []));
  for (const element of elements) {
    translateAttribute(element, "placeholder", lang);
    translateAttribute(element, "aria-label", lang);
    translateAttribute(element, "title", lang);
  }
}

function scheduleApply(): void {
  window.requestAnimationFrame(() => translateTree(document.body, currentLanguage()));
}

/**
 * Text-only localization quality layer.
 *
 * It does not change layout, data, navigation, permissions or workflow behavior.
 * It only normalizes visible UI copy and accessibility labels across English,
 * Eastern Armenian and Russian, including legacy dashboard enhancers that were
 * originally shipped with English-only strings.
 */
export function FrontendLocaleQuality() {
  useEffect(() => {
    scheduleApply();
    const observer = new MutationObserver((records) => {
      const lang = currentLanguage();
      for (const record of records) {
        if (record.type === "characterData") translateTextNode(record.target as Text, lang);
        for (const node of Array.from(record.addedNodes)) translateTree(node, lang);
        if (record.type === "attributes" && record.target instanceof Element) {
          const name = record.attributeName;
          if (name === "placeholder" || name === "aria-label" || name === "title") translateAttribute(record.target, name, lang);
        }
      }
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["placeholder", "aria-label", "title"],
    });
    const refresh = () => scheduleApply();
    window.addEventListener("teta2-language-change", refresh);
    window.addEventListener("popstate", refresh);
    return () => {
      observer.disconnect();
      window.removeEventListener("teta2-language-change", refresh);
      window.removeEventListener("popstate", refresh);
    };
  }, []);
  return null;
}
