import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  Check,
  CheckCircle2,
  CircleAlert,
  ExternalLink,
  FileImage,
  FolderHeart,
  HeartPulse,
  Mail,
  MapPin,
  MessageCircle,
  Phone,
  Radar,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  UserRoundCheck,
} from "lucide-react";

import "./page-deck-v2.css";

type Lang = "en" | "hy" | "ru";
type DeckRoute = "/product" | "/how-it-works" | "/pricing" | "/clinical-safety" | "/about";

const WHO_AI = "https://www.who.int/publications/i/item/9789240029200";
const ADA_RADIOGRAPHS = "https://www.ada.org/resources/ada-library/oral-health-topics/x-rays-radiographs";
const TYPHON_LINKEDIN = "https://ru.linkedin.com/in/typhon-namira";
const PULSEMEAL_ABOUT = "https://pulsemealx.com/aboutUs.html";
const PULSEMEAL_HOME = "https://pulsemealx.com/";
const MAP_ADDRESS = "https://www.google.com/maps/search/?api=1&query=4%20Arshakunyats%20Avenue%2C%20Yerevan%2C%20Armenia";
const WHATSAPP = "https://wa.me/37493700251";

const COPY = {
  en: {
    shared: {
      ctaTagline: "OPG intelligence + patient follow-up",
      patient: "Patient",
      continuity: "Clinical continuity",
      builtTo: "Built to",
      notBuiltTo: "Not built to",
      normalUse: "NORMAL CLINICAL USE",
      aiSupports: "AI supports the dentist",
      aiReplaces: "AI replaces the dentist",
      responsible: "Responsible",
      notWithoutEvidence: "Not without evidence",
      whoSource: "WHO · Ethics and governance of AI for health",
      adaSource: "ADA / AAOMR",
      modelTuning: "AI model fine-tuning",
      marketCodeA: "AM",
      marketCodeR: "RU",
      typhonName: "Typhon Namira",
      vanName: "Van Arzoyan",
      telegramDisplay: "Telegram",
      typhonInitials: "TN",
      vanInitials: "VA"
    },
    product: {
      introK: "PRODUCT ARCHITECTURE", introT: "One clinical loop, built around the patient — not around an AI result.", introL: "Teta2 connects the panoramic image, AI-assisted possible findings, clinician review, the patient record and follow-up so each step remains part of one visible workflow.",
      loop: [["01","OPG enters the record","The panoramic image is stored with the patient instead of becoming a detached upload."],["02","AI-assisted review","The system surfaces possible findings for dentist examination."],["03","Clinician decides","The dentist reviews findings in context and confirms or rejects them."],["04","Follow-up stays visible","Problem- or tooth-based follow-up can remain connected to the same patient record."]],
      recordK:"PATIENT WORKSPACE", recordT:"The useful unit is not one image. It is the patient's clinical continuity.", recordL:"A patient workspace is designed to reconnect the pieces the clinic may need later — contact, imaging, review, follow-up and communication state.",
      recordItems:[["Patient identity & contact","Essential identity and contact context for the clinic."],["OPG history","Past panoramic images stay linked to the patient."],["Possible findings","AI-assisted findings remain reviewable, not final diagnoses."],["Review state","The clinic can distinguish unreviewed from reviewed findings."],["Follow-up timing","Scheduled or due work remains visible instead of disappearing into memory."],["Message state","Outreach can be tracked as a workflow state rather than assumed complete."]],
      visibilityK:"WHAT THE CLINIC CAN SEE", visibilityT:"Three layers of operational visibility.", visibilityL:"The product is intentionally designed around states that can be observed and acted on, instead of decorative analytics.",
      visibility:[["Clinical","What image and finding is being reviewed?","OPG, possible finding, review state"],["Patient","Who does this belong to?","Patient record, contact context, history"],["Follow-up","What is still waiting for action?","Timing, message state, patient return"]],
      scopeK:"INTENTIONAL SCOPE", scopeT:"Focused is a product decision, not a missing feature list.",
      does:["OPG-centered clinical workflow","AI-assisted possible findings for dentist review","Patient-specific records and history","Follow-up tied to clinical context","Visible message and return states"],
      doesnt:["No autonomous diagnosis","No guaranteed detection claim","No unpublished accuracy percentage","No replacement for clinical examination","Not positioned as a complete hospital ERP or billing suite"],
      fitK:"WHO IT IS FOR", fitT:"Best fit: clinics that already use panoramic imaging and want a tighter follow-up loop.", fitL:"Teta2 is most relevant where the clinic already has OPGs, patient records and follow-up work — but those steps are fragmented across people, files and messaging tools.",
      fit:["Dental clinics reviewing panoramic radiographs","Teams that want clinician review to remain explicit","Clinics that need patient-specific recall and follow-up visibility","Operators who prefer a narrow clinical workflow over a generic all-in-one CRM"],
      cta:"Request clinic access"
    },
    how: {
      introK:"WORKFLOW, NOT A BLACK BOX", introT:"What happens after the upload matters as much as the model output.", introL:"Teta2 makes the transitions explicit: who reviewed the finding, what follow-up exists, whether outreach was sent and whether the patient returned.",
      steps:[["01","Create patient","Start with the patient identity and contact context."],["02","Upload OPG","Attach the panoramic radiograph to that patient."],["03","Run AI-assisted analysis","Generate possible findings for professional review."],["04","Review clinically","The dentist examines and confirms or rejects findings."],["05","Keep the record","OPG, findings and review remain connected to the patient."],["06","Set follow-up","Create problem- or tooth-based timing where needed."],["07","Send outreach","Use the configured patient-messaging workflow."],["08","Track return","Keep the follow-up visible until the workflow moves forward."]],
      stateK:"STATE MACHINE", stateT:"The workflow is designed around explicit states, not assumptions.", stateL:"A state tells the clinic what has happened so far. It does not pretend the next step has already happened.",
      states:[["UNREVIEWED","A possible finding exists, but dentist review is still pending."],["REVIEWED","The finding has been examined by the clinician."],["SCHEDULED","A future follow-up has been created."],["DUE","The follow-up has reached its action window."],["SENDING / SENT","Patient outreach has a delivery state."],["RETURN","The patient comes back into the clinical workflow."]],
      handK:"THREE RESPONSIBILITY GATES", handT:"Automation can move information. Responsibility remains visible.",
      hand:[["AI → Dentist","The model surfaces possible findings; the dentist owns clinical interpretation."],["Dentist → Record","The review decision is stored with the patient and OPG history."],["Record → Patient","Follow-up outreach is connected to the clinical context instead of a generic reminder list."]],
      exceptionsK:"WHEN THE FLOW DOES NOT COMPLETE", exceptionsT:"The system should show unfinished work instead of hiding it.",
      exceptions:[["Review not completed","The finding remains visibly unreviewed."],["Follow-up becomes due","It remains due until the clinic moves the workflow forward."],["Message sent","Sent is a communication state, not proof of treatment."],["Patient has not returned","The workflow can remain open rather than being counted as a completed outcome."]],
      boundaryK:"AUTOMATION BOUNDARY", boundaryT:"Four things Teta2 deliberately does not infer on its own.", boundary:["A model output is not treated as a definitive diagnosis.","A sent message is not treated as a completed clinical result.","A follow-up state is not silently closed without workflow action.","Diagnosis and treatment decisions remain the clinician's responsibility."],
      cta:"Request access"
    },
    pricing: {
      introK:"CLINIC SUBSCRIPTION", introT:"Two markets. One clear monthly subscription model.", introL:"Pricing is shown per clinic per month. The Funding Plan is a limited launch price for the first 50 clinics in each market; this page does not claim that a slot is still available until access is confirmed.",
      standard:"Standard", funding:"Funding Plan", first50:"First 50 clinics", month:"/ month", marketA:"Armenia", marketR:"Russia",
      amdStandard:"49,000 AMD", amdFunding:"39,000 AMD", rubStandard:"14,000 RUB", rubFunding:"11,400 RUB",
      fundingK:"FUNDING PLAN", fundingT:"A launch price for the first 50 clinics — not a stripped-down product tier.", fundingL:"The Funding Plan is the early clinic price shown by Teta2 for the first 50 clinics in each market. Availability should be confirmed during access review because the website does not publish a live remaining-slot counter.",
      includeK:"WHAT THE SUBSCRIPTION COVERS", includeT:"The paid value is the workflow itself.", includeL:"The subscription is built around the same core product shown across the site — OPG review, patient continuity and follow-up visibility.",
      included:["AI-assisted OPG analysis","Possible findings for dentist examination","Visual OPG review workflow","Smart patient record","OPG and analysis history","Clinician review state","Problem/tooth-based follow-up timing","Patient messaging workflow","Follow-up dashboard visibility","Patient-return tracking"],
      fairK:"FAIR USE", fairT:"Normal clinical use is not priced with a per-OPG counter.", fairL:"Teta2's public product position is unlimited OPG analysis during an active subscription for normal clinical use. Fair Use applies to abnormal automated bulk processing or API abuse.",
      onboardK:"ACCESS PROCESS", onboardT:"Clinic access is provisioned deliberately.", onboardL:"Public self-service provisioning is not enabled yet. Access is requested, reviewed and then activated for a clinic workspace.",
      onboard:[["01","Request","Submit clinic and contact information."],["02","Review","Teta2 reviews the clinic access request before provisioning."],["03","Activate","Credentials and the clinic workspace are issued after approval."],["04","Continue","Renewal is intended to continue the same clinic workspace rather than start a separate record set."]],
      note:"The market prices above are the current prices supplied for Teta2. No hidden performance, regulatory or diagnostic guarantee is implied by the subscription price.", cta:"Request access"
    },
    safety: {
      introK:"CLINICAL SAFETY", introT:"Safety starts with the claims the product refuses to make.", introL:"Teta2 presents AI-assisted possible findings for dentist examination. It does not present model output as a definitive diagnosis and does not publish accuracy claims that have not been validated and released.",
      claimsK:"CLAIMS BOUNDARY", claimsT:"Responsible language keeps the decision boundary clear.",
      safe:["Possible finding","AI-assisted analysis","Requires dentist examination","Clinician reviewed / unreviewed","Follow-up scheduled / due"],
      unsafe:["Definitive diagnosis from AI alone","Guaranteed detection","Guaranteed clinical outcome","Unpublished accuracy percentage","Message sent = treatment completed"],
      humanK:"HUMAN IN THE LOOP", humanT:"The model can surface information. The clinician keeps the decision gate.", humanL:"WHO guidance on AI for health emphasizes ethics, accountability and appropriate human oversight. Teta2's workflow keeps model output reviewable rather than autonomous.",
      human:[["01","AI-assisted output"],["02","Dentist examination"],["03","Confirm / reject in context"],["04","Follow-up or care decision"]],
      imagingK:"IMAGING CONTEXT", imagingT:"An OPG is clinical evidence — not the entire clinical examination.", imagingL:"ADA and AAOMR guidance emphasizes clinical examination and patient-specific need when radiographic imaging is used for diagnosis, treatment planning and management. Teta2's use of OPGs should be understood inside that wider clinical context.",
      opsK:"OPERATIONAL HONESTY", opsT:"The interface should distinguish what happened from what is merely expected next.",
      ops:[["Finding exists","Does not mean diagnosis is complete."],["Clinician reviewed","Does not mean treatment occurred."],["Message sent","Does not mean patient understood, booked or returned."],["Follow-up due","Does not mean the clinic has acted yet."]],
      foot:"Teta2 is a clinical decision-support workflow. Professional examination, appropriate imaging selection and dentist responsibility remain necessary.", source:"Read source", cta:"Request access"
    },
    about: {
      introK:"ABOUT TETA2", introT:"A focused dental AI project being built in Yerevan.", introL:"Teta2 is being built around one narrow operational problem: connecting OPG review to a patient record and a visible follow-up workflow. This website presents it as a pre-incorporation software project — not as a claim of regulatory approval or autonomous clinical practice.",
      principle:"The radiograph should not become an isolated AI result. It should stay connected to the clinician, the patient and the next action.",
      teamK:"TEAM", teamT:"The people currently identified with the project.", teamL:"Roles below are intentionally narrow and factual. Public-source links are included where they exist.",
      typhonRole:"Founder · Teta2", vanRole:"Co-founder · Technical / AI model fine-tuning",
      typhonExperience:[["PulseMeal","Founder experience building an AR + AI restaurant technology startup in Yerevan."],["FinnoWay Armenia 2025","PulseMeal was publicly presented in the event's Startup Alley in Yerevan."],["Founders Event Horizon · 2026","Publicly organized founder-networking activity in Yerevan around startups, entrepreneurship and collaboration."]],
      vanBody:"Van Arzoyan has worked on Teta2's technical side, including AI model fine-tuning.",
      publicProfile:"Public profile", publicSource:"Public source",
      buildK:"HOW THE PROJECT IS BEING BUILT", buildT:"Narrow scope, visible states, and claims that can be defended.", build:[["01","Start with the OPG","Keep one imaging workflow at the center instead of expanding into every clinic function."],["02","Keep the dentist in control","Possible findings remain reviewable and clinical decisions stay with the dentist."],["03","Connect follow-up","The product continues beyond analysis into a patient-specific follow-up state."],["04","Avoid fake proof","No invented customer count, accuracy percentage, revenue metric or clinical outcome is used on this site."]],
      contactK:"CONTACT", contactT:"Talk directly to the Teta2 team.", contactL:"For clinic access, product questions, technical discussion or partnerships, use the channel that works best for you.",
      email:"Email", phone:"Phone", whatsapp:"WhatsApp", telegram:"Telegram", office:"Office", address:"4 Arshakunyats Avenue, Yerevan 0023, Armenia", cta:"Request clinic access"
    }
  },
  hy: {
    shared: {
      ctaTagline: "Պանորամային ռենտգենի վերլուծություն և պացիենտի հետագա վերահսկում",
      patient: "Պացիենտ",
      continuity: "Կլինիկական շարունակականություն",
      builtTo: "Նախատեսված է",
      notBuiltTo: "Նախատեսված չէ",
      normalUse: "ՍՈՎՈՐԱԿԱՆ ԿԼԻՆԻԿԱԿԱՆ ՕԳՏԱԳՈՐԾՈՒՄ",
      aiSupports: "Արհեստական բանականությունը աջակցում է ատամնաբույժին",
      aiReplaces: "Արհեստական բանականությունը փոխարինում է ատամնաբույժին",
      responsible: "Պատասխանատու ձևակերպումներ",
      notWithoutEvidence: "Չի ներկայացվում առանց ապացույցի",
      whoSource: "Առողջապահության համաշխարհային կազմակերպություն · Արհեստական բանականության էթիկա և կառավարում առողջապահությունում",
      adaSource: "Ամերիկյան ատամնաբուժական ասոցիացիա և դիմածնոտային ռադիոլոգիայի ակադեմիա",
      modelTuning: "Արհեստական բանականության մոդելի ճշգրտում",
      marketCodeA: "ՀՀ",
      marketCodeR: "ՌԴ",
      typhonName: "Թայֆոն Նամիրա",
      vanName: "Վան Արզոյան",
      telegramDisplay: "Տելեգրամ",
      typhonInitials: "ԹՆ",
      vanInitials: "ՎԱ"
    },
    product: {
      introK:"ԱՐՏԱԴՐԱՆՔԻ ՃԱՐՏԱՐԱՊԵՏՈՒԹՅՈՒՆ", introT:"Մեկ կլինիկական շղթա՝ կառուցված պացիենտի, ոչ թե արհեստական բանականության առանձին արդյունքի շուրջ։", introL:"Teta2-ը մեկ տեսանելի աշխատանքային ընթացքի մեջ միավորում է պանորամային ռենտգեն պատկերը, արհեստական բանականությամբ աջակցվող հնարավոր հայտնաբերումները, բժշկի վերանայումը, պացիենտի քարտը և հետագա վերահսկումը։",
      loop:[["01","Պանորամային պատկերը մտնում է պացիենտի քարտ","Պանորամային ռենտգեն պատկերը պահպանվում է հենց պացիենտի քարտում և չի մնում որպես առանձին վերբեռնում։"],["02","Արհեստական բանականությամբ աջակցվող վերլուծություն","Համակարգը ցույց է տալիս հնարավոր հայտնաբերումները՝ ատամնաբույժի մասնագիտական գնահատման համար։"],["03","Բժիշկն է որոշում","Ատամնաբույժը տվյալները դիտարկում է կլինիկական համատեքստում և հաստատում կամ մերժում է հնարավոր հայտնաբերումները։"],["04","Հետագա վերահսկումը մնում է տեսանելի","Խնդրի կամ կոնկրետ ատամի հետ կապված հետագա վերահսկումը պահպանվում է նույն պացիենտի քարտում։"]],
      recordK:"ՊԱՑԻԵՆՏԻ ՔԱՐՏ", recordT:"Արժեքավոր միավորը մեկ պատկեր չէ, այլ պացիենտի կլինիկական շարունակականությունը։", recordL:"Պացիենտի քարտը մեկ տեղում միավորում է կոնտակտային տվյալները, պատկերները, բժշկի վերանայումը, հետագա վերահսկումը և հաղորդակցության վիճակը։",
      recordItems:[["Պացիենտի ինքնություն և կապ","Կլինիկայի համար անհրաժեշտ հիմնական նույնականացման և կապի տվյալները։"],["Պանորամային պատկերների պատմություն","Նախորդ պանորամային ռենտգեն պատկերները կապված են մնում նույն պացիենտի հետ։"],["Հնարավոր հայտնաբերումներ","Արհեստական բանականությամբ առաջարկված արդյունքները ենթակա են բժշկի վերանայման և վերջնական ախտորոշում չեն։"],["Վերանայման վիճակ","Կլինիկան հստակ տարբերակում է դեռ չվերանայված և արդեն վերանայված արդյունքները։"],["Հետագա վերահսկման ժամկետներ","Պլանավորված կամ արդեն հասունացած գործողությունները մնում են տեսանելի։"],["Հաղորդագրության վիճակ","Պացիենտի հետ կապի ընթացքը գրանցվում է որպես հստակ վիճակ և չի համարվում ինքնաբերաբար ավարտված։"]],
      visibilityK:"ԻՆՉ Է ՏԵՍՆՈՒՄ ԿԼԻՆԻԿԱՆ", visibilityT:"Գործնական տեսանելիության երեք մակարդակ։", visibilityL:"Համակարգը կառուցված է այն վիճակների շուրջ, որոնք կարելի է տեսնել և որոնց հիման վրա կարելի է գործել՝ առանց ձևական վիճակագրության։",
      visibility:[["Կլինիկական","Ո՞ր պատկերն ու հնարավոր հայտնաբերումն է այժմ վերանայվում։","Պանորամային պատկեր, հնարավոր հայտնաբերում, վերանայման վիճակ"],["Պացիենտ","Ո՞ւմ է վերաբերում տվյալը։","Պացիենտի քարտ, կապի տվյալներ, պատմություն"],["Հետագա վերահսկում","Ի՞նչ գործողություն դեռ սպասում է կատարման։","Ժամկետ, հաղորդագրության վիճակ, պացիենտի վերադարձ"]],
      scopeK:"ԳԻՏԱԿՑՎԱԾ ՍԱՀՄԱՆՆԵՐ", scopeT:"Կենտրոնացված լինելը արտադրանքի գիտակցված ընտրությունն է, ոչ թե բաց թողնված գործառույթների ցուցակ։",
      does:["Պանորամային ռենտգենի շուրջ կառուցված կլինիկական աշխատանքային ընթացք","Արհեստական բանականությամբ աջակցվող հնարավոր հայտնաբերումներ՝ բժշկի վերանայման համար","Յուրաքանչյուր պացիենտի առանձին քարտ և պատմություն","Կլինիկական համատեքստին կապված հետագա վերահսկում","Հաղորդագրությունների և պացիենտի վերադարձի հստակ վիճակներ"],
      doesnt:["Ինքնուրույն ախտորոշում չի իրականացնում","Հայտնաբերման երաշխավորված արդյունք չի խոստանում","Չվավերացված ճշգրտության տոկոս չի հրապարակում","Չի փոխարինում կլինիկական զննմանը","Չի ներկայացվում որպես հիվանդանոցի ամբողջական կառավարման կամ հաշվարկային համակարգ"],
      fitK:"ՈՒՄ ՀԱՄԱՐ Է", fitT:"Առավել հարմար է այն կլինիկաներին, որոնք արդեն օգտագործում են պանորամային ռենտգեն և ցանկանում են ավելի հստակ վերահսկել պացիենտի հետագա ընթացքը։", fitL:"Teta2-ը հատկապես օգտակար է այն միջավայրում, որտեղ պանորամային պատկերները, պացիենտի քարտերը և հետագա վերահսկման աշխատանքը արդեն կան, բայց բաժանված են մարդկանց, ֆայլերի և հաղորդակցության տարբեր միջոցների միջև։",
      fit:["Պանորամային ռենտգեն պատկերներ վերանայող ատամնաբուժական կլինիկաներ","Թիմեր, որտեղ բժշկի վերանայումը պետք է հստակ և տեսանելի մնա","Կլինիկաներ, որոնց անհրաժեշտ է յուրաքանչյուր պացիենտի անհատական հիշեցման և հետագա վերահսկման տեսանելիություն","Կազմակերպություններ, որոնք նախընտրում են նեղ և կլինիկականորեն կենտրոնացված լուծում՝ ընդհանուր կառավարման համակարգի փոխարեն"],
      cta:"Հարցում ուղարկել կլինիկայի մուտքի համար"
    },
    how: {
      introK:"ԱՇԽԱՏԱՆՔԱՅԻՆ ԸՆԹԱՑՔ, ՈՉ ՍԵՎ ԱՐԿՂ", introT:"Վերբեռնումից հետո տեղի ունեցողը նույնքան կարևոր է, որքան մոդելի արդյունքը։", introL:"Teta2-ը հստակ ցույց է տալիս՝ ով է վերանայել հնարավոր հայտնաբերումը, ինչ հետագա վերահսկում է նախատեսված, ուղարկվել է արդյոք հաղորդագրություն և վերադարձել է արդյոք պացիենտը։",
      steps:[["01","Ստեղծել պացիենտի քարտ","Սկսեք պացիենտի ինքնության, կապի և անհրաժեշտ կլինիկական տվյալներից։"],["02","Վերբեռնել պանորամային պատկերը","Պացիենտի պանորամային ռենտգեն պատկերը կցեք նրա քարտին։"],["03","Կատարել աջակցվող վերլուծություն","Համակարգը ներկայացնում է հնարավոր հայտնաբերումներ՝ մասնագիտական վերանայման համար։"],["04","Կատարել կլինիկական վերանայում","Ատամնաբույժը զննում է արդյունքները և համատեքստում հաստատում կամ մերժում դրանք։"],["05","Պահպանել պատմությունը","Պատկերը, հնարավոր հայտնաբերումները և վերանայման արդյունքը մնում են նույն պացիենտի քարտում։"],["06","Սահմանել հետագա վերահսկումը","Անհրաժեշտության դեպքում սահմանեք խնդրի կամ ատամի հետ կապված հաջորդ գործողության ժամկետը։"],["07","Կապվել պացիենտի հետ","Ուղարկեք կլինիկայի կողմից նախատեսված հաղորդագրությունը պացիենտին։"],["08","Հետևել վերադարձին","Հետագա վերահսկումը բաց և տեսանելի պահեք մինչև պացիենտի վերադարձը կամ հաջորդ կլինիկական գործողությունը։"]],
      stateK:"ՎԻՃԱԿՆԵՐԻ ՇՂԹԱ", stateT:"Աշխատանքային ընթացքը կառուցված է հստակ վիճակների, ոչ թե ենթադրությունների շուրջ։", stateL:"Յուրաքանչյուր վիճակ ցույց է տալիս՝ ինչ է արդեն կատարվել, առանց հաջորդ քայլը կատարված համարելու։",
      states:[["ՉՎԵՐԱՆԱՅՎԱԾ","Հնարավոր հայտնաբերումը կա, բայց ատամնաբույժի վերանայումը դեռ սպասվում է։"],["ՎԵՐԱՆԱՅՎԱԾ","Ատամնաբույժը ուսումնասիրել է հնարավոր հայտնաբերումը։"],["ՊԼԱՆԱՎՈՐՎԱԾ","Ստեղծվել է հետագա վերահսկման ապագա գործողություն։"],["ԺԱՄԿԵՏԸ ՀԱՍԵԼ Է","Հետագա գործողության նախատեսված ժամկետը հասել է։"],["ՈՒՂԱՐԿՎՈՒՄ Է / ՈՒՂԱՐԿՎԱԾ","Պացիենտին ուղարկվող հաղորդագրության առաքման վիճակը հստակ գրանցվում է։"],["ՎԵՐԱԴԱՐՁ","Պացիենտը վերադառնում է կլինիկական ընթացքի մեջ։"]],
      handK:"ՊԱՏԱՍԽԱՆԱՏՎՈՒԹՅԱՆ ԵՐԵՔ ՍԱՀՄԱՆ", handT:"Ավտոմատացումը կարող է փոխանցել տեղեկությունը, բայց պատասխանատվությունը մնում է հստակ։",
      hand:[["ԱԲ → ատամնաբույժ","Համակարգը ներկայացնում է հնարավոր հայտնաբերումները, իսկ կլինիկական մեկնաբանության պատասխանատվությունը կրում է ատամնաբույժը։"],["Ատամնաբույժ → պացիենտի քարտ","Բժշկի որոշումը պահպանվում է պացիենտի և նրա պատկերների պատմության հետ միասին։"],["Պացիենտի քարտ → պացիենտ","Հետագա կապը կապված է իրական կլինիկական համատեքստին և չի դառնում ընդհանուր հիշեցումների ցանկ։"]],
      exceptionsK:"ԵՐԲ ԸՆԹԱՑՔԸ ՉԻ ԱՎԱՐՏՎՈՒՄ", exceptionsT:"Համակարգը պետք է ցույց տա չավարտված աշխատանքը, ոչ թե թաքցնի այն։",
      exceptions:[["Վերանայումը չի ավարտվել","Հնարավոր հայտնաբերումը շարունակում է հստակ նշված մնալ որպես չվերանայված։"],["Հետագա գործողության ժամկետը հասել է","Այն մնում է սպասվող գործողությունների մեջ մինչև կլինիկան առաջ տանի ընթացքը։"],["Հաղորդագրությունն ուղարկվել է","Ուղարկված հաղորդագրությունը կապի վիճակ է և բուժման ապացույց չէ։"],["Պացիենտը չի վերադարձել","Ընթացքը կարող է բաց մնալ և չհամարվել ավարտված արդյունք։"]],
      boundaryK:"ԱՎՏՈՄԱՏԱՑՄԱՆ ՍԱՀՄԱՆՆԵՐ", boundaryT:"Չորս բան, որոնք Teta2-ը դիտավորյալ ինքնուրույն չի ենթադրում։", boundary:["Մոդելի արդյունքը չի համարվում վերջնական ախտորոշում։","Ուղարկված հաղորդագրությունը չի համարվում ավարտված կլինիկական արդյունք։","Հետագա վերահսկման վիճակը չի փակվում ինքնաբերաբար՝ առանց համապատասխան գործողության։","Ախտորոշման և բուժման որոշումները մնում են ատամնաբույժի պատասխանատվության տակ։"],
      cta:"Հարցում ուղարկել մուտքի համար"
    },
    pricing: {
      introK:"ԿԼԻՆԻԿԱՅԻ ԲԱԺԱՆՈՐԴԱԳՐՈՒԹՅՈՒՆ", introT:"Երկու շուկա։ Մեկ պարզ ամսական բաժանորդագրություն։", introL:"Գինը նշված է մեկ կլինիկայի համար՝ ամսական։ Յուրաքանչյուր շուկայում առաջին 50 կլինիկաների համար գործում է սահմանափակ մեկնարկային սակագին։ Դրա հասանելիությունը հաստատվում է մուտքի հարցման վերանայման ընթացքում։",
      standard:"Ստանդարտ", funding:"Մեկնարկային սակագին", first50:"Առաջին 50 կլինիկաները", month:"/ ամիս", marketA:"Հայաստան", marketR:"Ռուսաստան",
      amdStandard:"49 000 դր.", amdFunding:"39 000 դր.", rubStandard:"14 000 ₽", rubFunding:"11 400 ₽",
      fundingK:"ՄԵԿՆԱՐԿԱՅԻՆ ՍԱԿԱԳԻՆ", fundingT:"Մեկնարկային գին առաջին 50 կլինիկաների համար՝ առանց արտադրանքի հնարավորությունները սահմանափակելու։", fundingL:"Մեկնարկային սակագինը Teta2-ի վաղ գործընկեր կլինիկաների համար նախատեսված գինն է՝ յուրաքանչյուր շուկայում առաջին 50 կլինիկաների համար։ Կայքը ազատ տեղերի կենդանի հաշվիչ չի հրապարակում, այդ պատճառով հասանելիությունը հաստատվում է մուտքի հարցման վերանայման ընթացքում։",
      includeK:"ԻՆՉ Է ՆԵՐԱՌՎԱԾ ԲԱԺԱՆՈՐԴԱԳՐՈՒԹՅԱՆ ՄԵՋ", includeT:"Վճարվող արժեքը հենց ամբողջ աշխատանքային ընթացքն է։", includeL:"Բաժանորդագրությունը ներառում է նույն հիմնական շղթան, որը ներկայացված է կայքում՝ պանորամային պատկերի վերանայում, պացիենտի կլինիկական շարունակականություն և հետագա վերահսկման տեսանելիություն։",
      included:["Պանորամային ռենտգենի՝ արհեստական բանականությամբ աջակցվող վերլուծություն","Հնարավոր հայտնաբերումներ՝ ատամնաբույժի մասնագիտական գնահատման համար","Պանորամային պատկերի տեսողական վերանայման ընթացք","Պացիենտի խելացի կլինիկական քարտ","Պատկերների և վերլուծությունների պատմություն","Բժշկի վերանայման հստակ վիճակ","Խնդրի կամ ատամի հիմքով հետագա վերահսկման ժամկետավորում","Պացիենտների հետ հաղորդակցության աշխատանքային ընթացք","Հետագա վերահսկման վահանակ","Պացիենտի վերադարձի հետևում"],
      fairK:"ԱՐԴԱՐ ՕԳՏԱԳՈՐԾՈՒՄ", fairT:"Սովորական կլինիկական օգտագործման դեպքում յուրաքանչյուր պանորամային պատկերի համար առանձին հաշվարկ չկա։", fairL:"Ակտիվ բաժանորդագրության ընթացքում պանորամային պատկերների վերլուծությունը սովորական կլինիկական օգտագործման համար սահմանափակված չէ պատկերների քանակով։ Արդար օգտագործման կանոնները կիրառվում են անսովոր զանգվածային ավտոմատ մշակման կամ ծրագրային միջերեսի չարաշահման դեպքում։",
      onboardK:"ՄՈՒՏՔԻ ՏՐԱՄԱԴՐՄԱՆ ԳՈՐԾԸՆԹԱՑ", onboardT:"Կլինիկայի մուտքը տրամադրվում է վերահսկված և հստակ ընթացքով։", onboardL:"Հանրային ինքնասպասարկվող ակտիվացումը դեռ միացված չէ։ Կլինիկան ուղարկում է հարցում, այն վերանայվում է, ապա ստեղծվում և ակտիվացվում է կլինիկայի աշխատանքային միջավայրը։",
      onboard:[["01","Հարցում","Ուղարկեք կլինիկայի և կապի պատասխանատու անձի տվյալները։"],["02","Վերանայում","Teta2-ը ստուգում և վերանայում է կլինիկայի մուտքի հարցումը։"],["03","Ակտիվացում","Հաստատումից հետո տրամադրվում են մուտքի տվյալները և կլինիկայի աշխատանքային միջավայրը։"],["04","Շարունակություն","Բաժանորդագրության երկարաձգումը շարունակում է նույն կլինիկայի աշխատանքային միջավայրը և պատմությունը։"]],
      note:"Վերևում նշված գները Teta2-ի ներկայիս հրապարակային սակագներն են։ Բաժանորդագրության արժեքը չի նշանակում կլինիկական արդյունավետության, կարգավորող հաստատման կամ ախտորոշիչ արդյունքի որևէ երաշխիք։", cta:"Հարցում ուղարկել մուտքի համար"
    },
    safety: {
      introK:"ԿԼԻՆԻԿԱԿԱՆ ԱՆՎՏԱՆԳՈՒԹՅՈՒՆ", introT:"Անվտանգությունը սկսվում է այն պնդումներից, որոնք արտադրանքը գիտակցված կերպով չի անում։", introL:"Teta2-ը ներկայացնում է արհեստական բանականությամբ աջակցվող հնարավոր հայտնաբերումներ՝ ատամնաբույժի մասնագիտական գնահատման համար։ Մոդելի արդյունքը չի ներկայացվում որպես վերջնական ախտորոշում, և չվավերացված ճշգրտության ցուցանիշներ չեն հրապարակվում։",
      claimsK:"ՊՆԴՈՒՄՆԵՐԻ ՍԱՀՄԱՆՆԵՐ", claimsT:"Պատասխանատու ձևակերպումները հստակ պահում են բժշկական որոշման սահմանը։",
      safe:["Հնարավոր հայտնաբերում","Արհեստական բանականությամբ աջակցվող վերլուծություն","Պահանջում է ատամնաբույժի զննում","Վերանայված / չվերանայված բժշկի կողմից","Հետագա վերահսկումը պլանավորված է / ժամկետը հասել է"],
      unsafe:["Վերջնական ախտորոշում՝ միայն արհեստական բանականության հիման վրա","Հայտնաբերման երաշխավորված արդյունք","Երաշխավորված կլինիկական արդյունք","Չհրապարակված կամ չվավերացված ճշգրտության տոկոս","Հաղորդագրությունն ուղարկվել է = բուժումն ավարտված է"],
      humanK:"ՄԱՐԴԸ ՈՐՈՇՄԱՆ ՇՂԹԱՅՈՒՄ", humanT:"Համակարգը կարող է ներկայացնել տեղեկատվությունը, բայց կլինիկական որոշման իրավասությունը մնում է բժշկին։", humanL:"Առողջապահության համաշխարհային կազմակերպության՝ առողջապահությունում արհեստական բանականության կիրառման ուղեցույցները շեշտում են էթիկան, հաշվետվողականությունը և մարդու պատշաճ վերահսկողությունը։ Teta2-ում մոդելի արդյունքները ենթակա են բժշկի վերանայման և ինքնավար չեն։",
      human:[["01","Արհեստական բանականությամբ աջակցվող արդյունք"],["02","Ատամնաբույժի զննում"],["03","Հաստատում կամ մերժում կլինիկական համատեքստում"],["04","Հետագա վերահսկման կամ բուժման որոշում"]],
      imagingK:"ՊԱՏԿԵՐԱՅԻՆ ՀԱՄԱՏԵՔՍՏ", imagingT:"Պանորամային ռենտգեն պատկերը կլինիկական ապացույցի մի մասն է, ոչ ամբողջ կլինիկական զննումը։", imagingL:"Ամերիկյան ատամնաբուժական ասոցիացիայի և բերանի ու դիմածնոտային ռադիոլոգիայի մասնագիտական ուղեցույցները շեշտում են կլինիկական զննումը և յուրաքանչյուր պացիենտի անհատական անհրաժեշտությունը՝ ռենտգեն պատկերները ախտորոշման, բուժման պլանավորման և վերահսկման համար կիրառելիս։",
      opsK:"ԳՈՐԾԸՆԹԱՑԻ ԹԱՓԱՆՑԻԿՈՒԹՅՈՒՆ", opsT:"Միջերեսը պետք է տարբերակի այն, ինչ արդեն կատարվել է, այն քայլից, որը պարզապես սպասվում է։",
      ops:[["Հնարավոր հայտնաբերում կա","Սա չի նշանակում, որ ախտորոշումն ավարտված է։"],["Բժիշկը վերանայել է","Սա չի նշանակում, որ բուժումն իրականացվել է։"],["Հաղորդագրությունն ուղարկվել է","Սա չի նշանակում, որ պացիենտը հասկացել է, գրանցվել կամ վերադարձել է։"],["Հետագա գործողության ժամկետը հասել է","Սա չի նշանակում, որ կլինիկան արդեն կատարել է անհրաժեշտ գործողությունը։"]],
      foot:"Teta2-ը կլինիկական որոշումների աջակցման աշխատանքային համակարգ է։ Մասնագիտական զննումը, պատկերային հետազոտության ճիշտ ընտրությունը և ատամնաբույժի պատասխանատվությունը շարունակում են մնալ անհրաժեշտ։", source:"Բացել աղբյուրը", cta:"Հարցում ուղարկել մուտքի համար"
    },
    about: {
      introK:"TETA2-Ի ՄԱՍԻՆ", introT:"Կենտրոնացված ատամնաբուժական արհեստական բանականության նախագիծ, որը ստեղծվում է Երևանում։", introL:"Teta2-ը ստեղծվում է մեկ հստակ գործնական խնդրի շուրջ՝ պանորամային ռենտգենի վերանայումը կապել պացիենտի քարտի և տեսանելի հետագա վերահսկման ընթացքի հետ։ Կայքը նախագիծը ներկայացնում է որպես դեռ չգրանցված ծրագրային նախաձեռնություն, այլ ոչ որպես կարգավորող հաստատման կամ ինքնավար կլինիկական գործունեության պնդում։",
      principle:"Ռենտգեն պատկերը չպետք է վերածվի արհեստական բանականության մեկուսացված արդյունքի։ Այն պետք է կապված մնա բժշկի, պացիենտի և հաջորդ անհրաժեշտ գործողության հետ։",
      teamK:"ԹԻՄ", teamT:"Մարդիկ, որոնք ներկայում ներգրավված են նախագծում։", teamL:"Ստորև նշված դերերը դիտավորյալ ներկայացված են հստակ և փաստական ձևով։ Հասանելի լինելու դեպքում կցված են նաև հանրային աղբյուրներ։",
      typhonRole:"Հիմնադիր · Teta2", vanRole:"Համահիմնադիր · տեխնիկական ուղղություն և արհեստական բանականության մոդելի ճշգրտում",
      typhonExperience:[["PulseMeal","Հիմնադրի փորձ՝ Երևանում լրացված իրականության և արհեստական բանականության վրա հիմնված ռեստորանային տեխնոլոգիական նորաստեղծ ընկերություն ստեղծելու գործում։"],["ՖիննոՈւեյ Հայաստան 2025","PulseMeal-ը Երևանում հրապարակայնորեն ներկայացվել է միջոցառման նորաստեղծ ընկերությունների ցուցադրական հատվածում։"],["Ֆաունդերս Իվենթ Հորայզոն · 2026","Երևանում կազմակերպված հիմնադիրների հանրային հանդիպումներ՝ նորաստեղծ ընկերությունների, ձեռնարկատիրության և համագործակցության շուրջ։"]],
      vanBody:"Վան Արզոյանը մասնակցել է Teta2-ի տեխնիկական աշխատանքներին, այդ թվում՝ արհեստական բանականության մոդելի ճշգրտմանը։",
      publicProfile:"Հանրային պրոֆիլ", publicSource:"Հանրային աղբյուր",
      buildK:"ԻՆՉՊԵՍ Է ԿԱՌՈՒՑՎՈՒՄ ՆԱԽԱԳԻԾԸ", buildT:"Նեղ և հստակ սահմաններ, տեսանելի վիճակներ և պաշտպանելի պնդումներ։", build:[["01","Սկսել պանորամային ռենտգենից","Կենտրոնում պահել մեկ պատկերային աշխատանքային ընթացք՝ չփորձելով ընդգրկել կլինիկայի բոլոր գործառույթները։"],["02","Բժիշկը մնում է վերահսկողության կենտրոնում","Հնարավոր հայտնաբերումները ենթակա են վերանայման, իսկ կլինիկական որոշումները մնում են ատամնաբույժին։"],["03","Կապել հետագա վերահսկումը","Վերլուծությունից հետո համակարգը շարունակում է աշխատել պացիենտի անհատական հետագա վերահսկման վրա։"],["04","Չստեղծել կեղծ ապացույցներ","Կայքում չեն օգտագործվում հորինված հաճախորդների թվեր, ճշգրտության տոկոսներ, եկամտի ցուցանիշներ կամ կլինիկական արդյունքներ։"]],
      contactK:"ԿԱՊ", contactT:"Կապվեք անմիջապես Teta2-ի թիմի հետ։", contactL:"Կլինիկայի մուտքի, արտադրանքի, տեխնիկական հարցերի կամ գործընկերության համար ընտրեք ձեզ հարմար կապի եղանակը։",
      email:"Էլ. փոստ", phone:"Հեռախոս", whatsapp:"Վոթսափ", telegram:"Տելեգրամ", office:"Գրասենյակ", address:"Արշակունյաց պողոտա 4, Երևան 0023, Հայաստան", cta:"Հարցում ուղարկել կլինիկայի մուտքի համար"
    }
  },
  ru: {
    shared: {
      ctaTagline: "Анализ панорамных снимков и последующее наблюдение пациента",
      patient: "Пациент",
      continuity: "Непрерывность клинического наблюдения",
      builtTo: "Предназначено для",
      notBuiltTo: "Не предназначено для",
      normalUse: "ОБЫЧНОЕ КЛИНИЧЕСКОЕ ИСПОЛЬЗОВАНИЕ",
      aiSupports: "ИИ помогает стоматологу",
      aiReplaces: "ИИ заменяет стоматолога",
      responsible: "Корректные формулировки",
      notWithoutEvidence: "Не заявляется без доказательств",
      whoSource: "Всемирная организация здравоохранения · Этика и управление ИИ в здравоохранении",
      adaSource: "Американская стоматологическая ассоциация и академия челюстно-лицевой радиологии",
      modelTuning: "Настройка модели искусственного интеллекта",
      marketCodeA: "АМ",
      marketCodeR: "РФ",
      typhonName: "Тайфон Намира",
      vanName: "Ван Арзоян",
      telegramDisplay: "Телеграм",
      typhonInitials: "ТН",
      vanInitials: "ВА"
    },
    product: {
      introK:"АРХИТЕКТУРА ПРОДУКТА", introT:"Единый клинический цикл, построенный вокруг пациента, а не вокруг отдельного результата ИИ.", introL:"Teta2 объединяет панорамный снимок, возможные находки, предложенные ИИ, проверку врачом, карту пациента и последующее наблюдение в один прозрачный рабочий процесс.",
      loop:[["01","Панорамный снимок попадает в карту пациента","Снимок хранится вместе с картой пациента, а не остается отдельной загрузкой."],["02","Анализ с поддержкой ИИ","Система показывает возможные находки для профессиональной оценки стоматологом."],["03","Решение принимает врач","Стоматолог оценивает находки в клиническом контексте и подтверждает или отклоняет их."],["04","Последующее наблюдение остается видимым","Контроль, связанный с конкретной проблемой или зубом, остается привязан к той же карте пациента."]],
      recordK:"КАРТА ПАЦИЕНТА", recordT:"Полезная единица — не отдельный снимок, а непрерывность клинической истории пациента.", recordL:"Карта пациента объединяет контактные данные, снимки, врачебную проверку, последующее наблюдение и состояние связи с пациентом в одном месте.",
      recordItems:[["Данные пациента и контакт","Основные идентификационные и контактные сведения, необходимые клинике."],["История панорамных снимков","Предыдущие панорамные снимки остаются связаны с тем же пациентом."],["Возможные находки","Результаты, предложенные ИИ, подлежат проверке врачом и не являются окончательным диагнозом."],["Состояние проверки","Клиника четко различает еще не проверенные и уже проверенные результаты."],["Сроки последующего наблюдения","Запланированные или наступившие действия остаются видимыми и не теряются."],["Состояние сообщения","Связь с пациентом отслеживается как отдельное состояние процесса и не считается автоматически завершенной."]],
      visibilityK:"ЧТО ВИДИТ КЛИНИКА", visibilityT:"Три уровня практической прозрачности.", visibilityL:"Система построена вокруг состояний, которые можно увидеть и на основании которых можно действовать, а не вокруг декоративной статистики.",
      visibility:[["Клинический уровень","Какой снимок и какая возможная находка сейчас проверяются?","Панорамный снимок, возможная находка, состояние проверки"],["Пациент","К какому пациенту относятся данные?","Карта пациента, контактные сведения, история"],["Последующее наблюдение","Какое действие еще ожидает выполнения?","Срок, состояние сообщения, возвращение пациента"]],
      scopeK:"ОСОЗНАННЫЕ ГРАНИЦЫ", scopeT:"Узкая специализация — это осознанное решение продукта, а не список недостающих функций.",
      does:["Клинический процесс, построенный вокруг панорамной рентгенографии","Возможные находки с поддержкой ИИ для проверки стоматологом","Отдельная карта и история каждого пациента","Последующее наблюдение, связанное с клиническим контекстом","Явные состояния сообщений и возвращения пациента"],
      doesnt:["Не выполняет автономную диагностику","Не обещает гарантированное выявление патологий","Не публикует неподтвержденные показатели точности","Не заменяет клинический осмотр","Не позиционируется как полная больничная система управления или расчетов"],
      fitK:"ДЛЯ КОГО", fitT:"Лучше всего подходит клиникам, которые уже используют панорамные снимки и хотят надежнее контролировать дальнейший путь пациента.", fitL:"Teta2 особенно полезен там, где панорамные снимки, карты пациентов и задачи последующего наблюдения уже существуют, но разрознены между сотрудниками, файлами и средствами связи.",
      fit:["Стоматологические клиники, работающие с панорамными снимками","Команды, которым важно явно сохранять этап врачебной проверки","Клиники, которым нужна персональная система напоминаний и последующего наблюдения для каждого пациента","Организации, предпочитающие узкий клинический процесс универсальной системе управления"],
      cta:"Запросить доступ для клиники"
    },
    how: {
      introK:"РАБОЧИЙ ПРОЦЕСС, А НЕ ЧЕРНЫЙ ЯЩИК", introT:"То, что происходит после загрузки снимка, не менее важно, чем результат модели.", introL:"Teta2 явно показывает, кто проверил возможную находку, какое последующее наблюдение назначено, было ли отправлено сообщение и вернулся ли пациент.",
      steps:[["01","Создать карту пациента","Начните с данных пациента, контактов и необходимого клинического контекста."],["02","Загрузить панорамный снимок","Прикрепите панорамный рентгеновский снимок к карте пациента."],["03","Выполнить анализ с поддержкой ИИ","Система показывает возможные находки для профессиональной проверки."],["04","Провести клиническую проверку","Стоматолог изучает результаты и подтверждает или отклоняет их с учетом клинического контекста."],["05","Сохранить историю","Снимок, возможные находки и решение врача остаются в карте пациента."],["06","Назначить последующее наблюдение","При необходимости задайте срок следующего действия для конкретной проблемы или зуба."],["07","Связаться с пациентом","Отправьте пациенту подготовленное клиникой сообщение."],["08","Отслеживать возвращение","Сохраняйте задачу наблюдения открытой и видимой до возвращения пациента или следующего клинического действия."]],
      stateK:"ЦЕПОЧКА СОСТОЯНИЙ", stateT:"Рабочий процесс строится на четких состояниях, а не на предположениях.", stateL:"Каждое состояние показывает, что уже произошло, не выдавая следующий шаг за выполненный.",
      states:[["НЕ ПРОВЕРЕНО","Возможная находка есть, но проверка стоматологом еще ожидается."],["ПРОВЕРЕНО","Стоматолог изучил возможную находку."],["ЗАПЛАНИРОВАНО","Создано будущее действие по последующему наблюдению."],["СРОК НАСТУПИЛ","Наступил срок запланированного действия."],["ОТПРАВЛЯЕТСЯ / ОТПРАВЛЕНО","Состояние доставки сообщения пациенту явно фиксируется."],["ВОЗВРАЩЕНИЕ","Пациент возвращается в клинический процесс."]],
      handK:"ТРИ ГРАНИЦЫ ОТВЕТСТВЕННОСТИ", handT:"Автоматизация может передавать информацию, но ответственность остается прозрачной.",
      hand:[["ИИ → стоматолог","Система показывает возможные находки, а за их клиническую интерпретацию отвечает стоматолог."],["Стоматолог → карта пациента","Решение врача сохраняется вместе с картой пациента и историей снимков."],["Карта пациента → пациент","Связь с пациентом опирается на реальный клинический контекст, а не на общий список напоминаний."]],
      exceptionsK:"ЕСЛИ ПРОЦЕСС НЕ ЗАВЕРШЕН", exceptionsT:"Система должна показывать незавершенную работу, а не скрывать ее.",
      exceptions:[["Проверка не завершена","Возможная находка остается явно помеченной как непроверенная."],["Наступил срок действия","Задача остается ожидающей, пока клиника не продвинет процесс дальше."],["Сообщение отправлено","Факт отправки — это состояние связи, а не доказательство проведенного лечения."],["Пациент не вернулся","Процесс может оставаться открытым и не считаться завершенным результатом."]],
      boundaryK:"ГРАНИЦЫ АВТОМАТИЗАЦИИ", boundaryT:"Четыре вещи, которые Teta2 намеренно не определяет самостоятельно.", boundary:["Результат модели не считается окончательным диагнозом.","Отправленное сообщение не считается завершенным клиническим результатом.","Состояние последующего наблюдения не закрывается автоматически без соответствующего действия.","Решения о диагнозе и лечении остаются ответственностью стоматолога."],
      cta:"Запросить доступ"
    },
    pricing: {
      introK:"ПОДПИСКА ДЛЯ КЛИНИКИ", introT:"Два рынка. Одна понятная ежемесячная подписка.", introL:"Цена указана за одну клинику в месяц. Для первых 50 клиник на каждом рынке действует ограниченный стартовый тариф. Его доступность подтверждается при рассмотрении заявки на доступ.",
      standard:"Стандартный", funding:"Стартовый тариф", first50:"Первые 50 клиник", month:"/ месяц", marketA:"Армения", marketR:"Россия",
      amdStandard:"49 000 драм", amdFunding:"39 000 драм", rubStandard:"14 000 ₽", rubFunding:"11 400 ₽",
      fundingK:"СТАРТОВЫЙ ТАРИФ", fundingT:"Стартовая цена для первых 50 клиник без урезания возможностей продукта.", fundingL:"Стартовый тариф — это цена для первых партнерских клиник Teta2: она действует для первых 50 клиник на каждом рынке. Сайт не показывает счетчик оставшихся мест в реальном времени, поэтому доступность подтверждается при рассмотрении заявки.",
      includeK:"ЧТО ВХОДИТ В ПОДПИСКУ", includeT:"Оплачиваемая ценность — весь рабочий процесс целиком.", includeL:"Подписка охватывает тот же основной цикл, который показан на сайте: проверку панорамного снимка, непрерывность истории пациента и видимость последующего наблюдения.",
      included:["Анализ панорамного снимка с поддержкой ИИ","Возможные находки для профессиональной оценки стоматологом","Визуальная проверка панорамного снимка","Умная клиническая карта пациента","История снимков и анализов","Явное состояние врачебной проверки","Сроки наблюдения по конкретной проблеме или зубу","Процесс связи с пациентом","Панель последующего наблюдения","Отслеживание возвращения пациента"],
      fairK:"ДОБРОСОВЕСТНОЕ ИСПОЛЬЗОВАНИЕ", fairT:"При обычной клинической работе нет отдельной оплаты за каждый панорамный снимок.", fairL:"Во время активной подписки анализ панорамных снимков для обычного клинического использования не ограничивается счетчиком снимков. Правила добросовестного использования применяются к необычной массовой автоматической обработке или злоупотреблению программным интерфейсом.",
      onboardK:"ПОРЯДОК ПРЕДОСТАВЛЕНИЯ ДОСТУПА", onboardT:"Доступ клиники предоставляется по контролируемому и понятному процессу.", onboardL:"Публичная самостоятельная активация пока не включена. Клиника отправляет заявку, она проходит проверку, после чего создается и активируется рабочее пространство клиники.",
      onboard:[["01","Заявка","Отправьте данные клиники и контактного лица."],["02","Проверка","Teta2 рассматривает заявку клиники на доступ."],["03","Активация","После одобрения выдаются данные для входа и рабочее пространство клиники."],["04","Продолжение","Продление подписки сохраняет то же рабочее пространство и историю клиники."]],
      note:"Указанные выше цены — текущие публичные тарифы Teta2. Стоимость подписки не означает гарантии клинической эффективности, регуляторного одобрения или диагностического результата.", cta:"Запросить доступ"
    },
    safety: {
      introK:"КЛИНИЧЕСКАЯ БЕЗОПАСНОСТЬ", introT:"Безопасность начинается с утверждений, от которых продукт сознательно отказывается.", introL:"Teta2 показывает возможные находки с поддержкой ИИ для профессиональной оценки стоматологом. Результат модели не выдается за окончательный диагноз, а неподтвержденные показатели точности не публикуются.",
      claimsK:"ГРАНИЦЫ УТВЕРЖДЕНИЙ", claimsT:"Корректные формулировки сохраняют ясную границу медицинского решения.",
      safe:["Возможная находка","Анализ с поддержкой ИИ","Требуется осмотр стоматолога","Проверено / не проверено стоматологом","Наблюдение запланировано / срок наступил"],
      unsafe:["Окончательный диагноз только на основании ИИ","Гарантированное выявление","Гарантированный клинический результат","Неопубликованный или неподтвержденный процент точности","Сообщение отправлено = лечение завершено"],
      humanK:"ЧЕЛОВЕК В ЦЕПОЧКЕ РЕШЕНИЯ", humanT:"Система может показать информацию, но право клинического решения остается за врачом.", humanL:"Рекомендации Всемирной организации здравоохранения по применению искусственного интеллекта в здравоохранении подчеркивают этику, подотчетность и надлежащий человеческий контроль. В Teta2 результаты модели подлежат врачебной проверке и не работают автономно.",
      human:[["01","Результат с поддержкой ИИ"],["02","Осмотр стоматологом"],["03","Подтверждение или отклонение в клиническом контексте"],["04","Решение о наблюдении или лечении"]],
      imagingK:"КОНТЕКСТ ВИЗУАЛИЗАЦИИ", imagingT:"Панорамный рентгеновский снимок — часть клинических данных, а не весь клинический осмотр.", imagingL:"Профессиональные рекомендации Американской стоматологической ассоциации и специалистов по челюстно-лицевой радиологии подчеркивают необходимость клинического осмотра и индивидуальных показаний при использовании рентгеновских изображений для диагностики, планирования лечения и наблюдения.",
      opsK:"ПРОЗРАЧНОСТЬ ПРОЦЕССА", opsT:"Интерфейс должен различать то, что уже произошло, и то, что только ожидается.",
      ops:[["Есть возможная находка","Это не означает, что диагноз уже установлен."],["Врач выполнил проверку","Это не означает, что лечение было проведено."],["Сообщение отправлено","Это не означает, что пациент понял сообщение, записался или вернулся."],["Наступил срок наблюдения","Это не означает, что клиника уже выполнила необходимое действие."]],
      foot:"Teta2 — система поддержки клинических решений. Профессиональный осмотр, обоснованный выбор визуализации и ответственность стоматолога остаются обязательными.", source:"Открыть источник", cta:"Запросить доступ"
    },
    about: {
      introK:"О TETA2", introT:"Специализированный проект стоматологического ИИ, создаваемый в Ереване.", introL:"Teta2 создается вокруг одной конкретной практической задачи: связать проверку панорамного снимка с картой пациента и видимым процессом последующего наблюдения. Сайт представляет проект как программную инициативу до регистрации юридического лица, а не как заявление о регуляторном одобрении или автономной клинической практике.",
      principle:"Рентгеновский снимок не должен превращаться в изолированный результат ИИ. Он должен оставаться связанным с врачом, пациентом и следующим необходимым действием.",
      teamK:"КОМАНДА", teamT:"Люди, которые сейчас участвуют в проекте.", teamL:"Роли ниже намеренно описаны узко и фактически. Там, где возможно, добавлены ссылки на открытые источники.",
      typhonRole:"Основатель · Teta2", vanRole:"Сооснователь · техническое направление и настройка модели искусственного интеллекта",
      typhonExperience:[["PulseMeal","Опыт основателя технологического стартапа в Ереване на основе дополненной реальности и искусственного интеллекта для ресторанной отрасли."],["Финноуэй Армения 2025","PulseMeal был публично представлен в Ереване в выставочной зоне стартапов мероприятия."],["Фаундерс Ивент Хорайзон · 2026","Публичные встречи основателей в Ереване, посвященные стартапам, предпринимательству и сотрудничеству."]],
      vanBody:"Ван Арзоян участвовал в технической работе над Teta2, включая настройку модели искусственного интеллекта.",
      publicProfile:"Открытый профиль", publicSource:"Открытый источник",
      buildK:"КАК СОЗДАЕТСЯ ПРОЕКТ", buildT:"Узкие и понятные границы, видимые состояния и утверждения, которые можно обосновать.", build:[["01","Начать с панорамного снимка","Сохранить один процесс визуализации в центре продукта, не пытаясь охватить все функции клиники."],["02","Оставить контроль за стоматологом","Возможные находки остаются проверяемыми, а клинические решения принимает стоматолог."],["03","Связать последующее наблюдение","После анализа система продолжает работу с индивидуальным наблюдением конкретного пациента."],["04","Не создавать искусственных доказательств","На сайте не используются вымышленные числа клиентов, проценты точности, показатели выручки или клинические результаты."]],
      contactK:"КОНТАКТЫ", contactT:"Свяжитесь напрямую с командой Teta2.", contactL:"По вопросам доступа клиники, продукта, технического обсуждения или партнерства выберите удобный способ связи.",
      email:"Эл. почта", phone:"Телефон", whatsapp:"Ватсап", telegram:"Телеграм", office:"Офис", address:"проспект Аршакуняц, 4, Ереван 0023, Армения", cta:"Запросить доступ для клиники"
    }
  }
} as const;

function Heading({kicker,title,lead}:{kicker:string;title:string;lead?:string}){return <header className="deck2-heading"><span><Sparkles size={14}/>{kicker}</span><h2>{title}</h2>{lead&&<p>{lead}</p>}</header>}
function Cta({lang,label}:{lang:Lang;label:string}){const s=COPY[lang].shared;return <div className="deck2-cta"><div><b>Teta2</b><span>{s.ctaTagline}</span></div><a href="/register">{label}<ArrowRight/></a></div>}

function ProductPageDeck({lang}:{lang:Lang}){const c=COPY[lang].product;const s=COPY[lang].shared;return <div className="deck2 deck2-product">
<section className="deck2-section deck2-intro"><Heading kicker={c.introK} title={c.introT} lead={c.introL}/><div className="deck2-loop">{c.loop.map(([n,t,b],i)=><article key={n}><span>{n}</span><div><strong>{t}</strong><p>{b}</p></div>{i<c.loop.length-1&&<ArrowRight/>}</article>)}</div></section>
<section className="deck2-section deck2-record"><Heading kicker={c.recordK} title={c.recordT} lead={c.recordL}/><div className="deck2-record-shell"><div className="deck2-record-spine"><UserRoundCheck/><b>{s.patient}</b><span>{s.continuity}</span></div><div className="deck2-record-grid">{c.recordItems.map(([t,b],i)=><article key={t}><small>0{i+1}</small><strong>{t}</strong><p>{b}</p></article>)}</div></div></section>
<section className="deck2-section deck2-visibility"><Heading kicker={c.visibilityK} title={c.visibilityT} lead={c.visibilityL}/><div className="deck2-visibility-stage">{c.visibility.map(([t,q,a],i)=><article key={t} className={`v${i+1}`}><span>{i===0?<Radar/>:i===1?<FolderHeart/>:<HeartPulse/>}</span><small>{t}</small><h3>{q}</h3><p>{a}</p></article>)}</div></section>
<section className="deck2-section deck2-scope"><Heading kicker={c.scopeK} title={c.scopeT}/><div className="deck2-scope-grid"><article><h3><CheckCircle2/>{s.builtTo}</h3>{c.does.map(x=><p key={x}><Check/>{x}</p>)}</article><article><h3><ShieldCheck/>{s.notBuiltTo}</h3>{c.doesnt.map(x=><p key={x}><span>×</span>{x}</p>)}</article></div></section>
<section className="deck2-section deck2-fit"><Heading kicker={c.fitK} title={c.fitT} lead={c.fitL}/><div className="deck2-fit-grid">{c.fit.map((x,i)=><article key={x}><b>0{i+1}</b><p>{x}</p></article>)}</div></section><Cta lang={lang} label={c.cta}/></div>}

function HowPageDeck({lang}:{lang:Lang}){const c=COPY[lang].how;return <div className="deck2 deck2-how">
<section className="deck2-section"><Heading kicker={c.introK} title={c.introT} lead={c.introL}/><div className="deck2-workflow-spine">{c.steps.map(([n,t,b])=><article key={n}><span>{n}</span><div><strong>{t}</strong><p>{b}</p></div></article>)}</div></section>
<section className="deck2-section deck2-state"><Heading kicker={c.stateK} title={c.stateT} lead={c.stateL}/><div className="deck2-state-board">{c.states.map(([t,b],i)=><article key={t}><i>{i+1}</i><strong>{t}</strong><p>{b}</p></article>)}</div></section>
<section className="deck2-section deck2-handoff"><Heading kicker={c.handK} title={c.handT}/><div className="deck2-handoff-flow">{c.hand.map(([t,b],i)=><article key={t}><span>{i===0?<BrainCircuit/>:i===1?<FolderHeart/>:<MessageCircle/>}</span><strong>{t}</strong><p>{b}</p></article>)}</div></section>
<section className="deck2-section deck2-exception"><Heading kicker={c.exceptionsK} title={c.exceptionsT}/><div className="deck2-exception-list">{c.exceptions.map(([t,b],i)=><article key={t}><b>0{i+1}</b><div><strong>{t}</strong><p>{b}</p></div></article>)}</div></section>
<section className="deck2-section deck2-boundary"><Heading kicker={c.boundaryK} title={c.boundaryT}/><div className="deck2-boundary-row">{c.boundary.map((x,i)=><article key={x}><CircleAlert/><span>0{i+1}</span><p>{x}</p></article>)}</div></section><Cta lang={lang} label={c.cta}/></div>}

function PricingPageDeck({lang}:{lang:Lang}){const c=COPY[lang].pricing;const s=COPY[lang].shared;return <div className="deck2 deck2-pricing">
<section className="deck2-section"><Heading kicker={c.introK} title={c.introT} lead={c.introL}/><div className="deck2-market-stage"><article className="armenia"><header><span>{s.marketCodeA}</span><strong>{c.marketA}</strong></header><div className="deck2-price-row"><div><small>{c.standard}</small><b>{c.amdStandard}</b><span>{c.month}</span></div><ArrowRight/><div className="fund"><small>{c.funding} · {c.first50}</small><b>{c.amdFunding}</b><span>{c.month}</span></div></div></article><article className="russia"><header><span>{s.marketCodeR}</span><strong>{c.marketR}</strong></header><div className="deck2-price-row"><div><small>{c.standard}</small><b>{c.rubStandard}</b><span>{c.month}</span></div><ArrowRight/><div className="fund"><small>{c.funding} · {c.first50}</small><b>{c.rubFunding}</b><span>{c.month}</span></div></div></article></div></section>
<section className="deck2-section deck2-funding"><Heading kicker={c.fundingK} title={c.fundingT} lead={c.fundingL}/><div className="deck2-50"><strong>50</strong><span>{c.first50}</span><div>{Array.from({length:10},(_,i)=><i key={i}/>)}</div></div></section>
<section className="deck2-section"><Heading kicker={c.includeK} title={c.includeT} lead={c.includeL}/><div className="deck2-inclusions">{c.included.map((x,i)=><article key={x}><span>{i<3?<FileImage/>:i<6?<FolderHeart/>:<HeartPulse/>}</span><p>{x}</p><Check/></article>)}</div></section>
<section className="deck2-section deck2-fair"><Heading kicker={c.fairK} title={c.fairT} lead={c.fairL}/><div className="deck2-infinity"><Activity/><b>∞</b><span>{s.normalUse}</span></div></section>
<section className="deck2-section"><Heading kicker={c.onboardK} title={c.onboardT} lead={c.onboardL}/><div className="deck2-onboard">{c.onboard.map(([n,t,b])=><article key={n}><span>{n}</span><strong>{t}</strong><p>{b}</p></article>)}</div><p className="deck2-note"><CircleAlert/>{c.note}</p></section><Cta lang={lang} label={c.cta}/></div>}

function SafetyPageDeck({lang}:{lang:Lang}){const c=COPY[lang].safety;const s=COPY[lang].shared;return <div className="deck2 deck2-safety">
<section className="deck2-section"><Heading kicker={c.introK} title={c.introT} lead={c.introL}/><div className="deck2-safety-signal"><ShieldCheck/><span>{s.aiSupports}</span><b>≠</b><span>{s.aiReplaces}</span></div></section>
<section className="deck2-section"><Heading kicker={c.claimsK} title={c.claimsT}/><div className="deck2-claims"><article className="safe"><h3><CheckCircle2/>{s.responsible}</h3>{c.safe.map(x=><p key={x}><Check/>{x}</p>)}</article><article className="guard"><h3><CircleAlert/>{s.notWithoutEvidence}</h3>{c.unsafe.map(x=><p key={x}><span>×</span>{x}</p>)}</article></div></section>
<section className="deck2-section"><Heading kicker={c.humanK} title={c.humanT} lead={c.humanL}/><div className="deck2-human-gate">{c.human.map(([n,t],i)=><article key={n}><b>{n}</b><span>{t}</span>{i<c.human.length-1&&<ArrowRight/>}</article>)}</div><a className="deck2-source" href={WHO_AI} target="_blank" rel="noreferrer">{s.whoSource}<ExternalLink/></a></section>
<section className="deck2-section deck2-imaging"><Heading kicker={c.imagingK} title={c.imagingT} lead={c.imagingL}/><div className="deck2-imaging-visual"><Stethoscope/><div/><Radar/></div><a className="deck2-source" href={ADA_RADIOGRAPHS} target="_blank" rel="noreferrer">{c.source} · {s.adaSource}<ExternalLink/></a></section>
<section className="deck2-section"><Heading kicker={c.opsK} title={c.opsT}/><div className="deck2-ops">{c.ops.map(([a,b],i)=><article key={a}><b>0{i+1}</b><strong>{a}</strong><ArrowRight/><p>{b}</p></article>)}</div><p className="deck2-note"><ShieldCheck/>{c.foot}</p></section><Cta lang={lang} label={c.cta}/></div>}

function AboutPageDeck({lang}:{lang:Lang}){const c=COPY[lang].about;const s=COPY[lang].shared;return <div className="deck2 deck2-about">
<section className="deck2-section deck2-about-intro"><Heading kicker={c.introK} title={c.introT} lead={c.introL}/><blockquote>{c.principle}</blockquote></section>
<section className="deck2-section"><Heading kicker={c.teamK} title={c.teamT} lead={c.teamL}/><div className="deck2-team"><article id="typhon-namira"><div className="deck2-person-head"><span>{s.typhonInitials}</span><div><small>{c.typhonRole}</small><h3>{s.typhonName}</h3></div></div><div className="deck2-experience">{c.typhonExperience.map(([t,b],i)=><div key={t}><b>0{i+1}</b><span><strong>{t}</strong><p>{b}</p></span></div>)}</div><div className="deck2-links"><a href={TYPHON_LINKEDIN} target="_blank" rel="noreferrer">{c.publicProfile}<ExternalLink/></a><a href={PULSEMEAL_ABOUT} target="_blank" rel="noreferrer">{c.publicSource}<ExternalLink/></a><a href={PULSEMEAL_HOME} target="_blank" rel="noreferrer">PulseMeal<ExternalLink/></a></div></article><article id="van-arzoyan"><div className="deck2-person-head"><span>{s.vanInitials}</span><div><small>{c.vanRole}</small><h3>{s.vanName}</h3></div></div><div className="deck2-tech-focus"><BrainCircuit/><strong>{s.modelTuning}</strong><p>{c.vanBody}</p></div></article></div></section>
<section className="deck2-section"><Heading kicker={c.buildK} title={c.buildT}/><div className="deck2-build">{c.build.map(([n,t,b])=><article key={n}><span>{n}</span><strong>{t}</strong><p>{b}</p></article>)}</div></section>
<section className="deck2-section deck2-contact"><Heading kicker={c.contactK} title={c.contactT} lead={c.contactL}/><div className="deck2-contact-grid"><a href="mailto:teta2support@gmail.com"><Mail/><span><small>{c.email}</small><strong>teta2support@gmail.com</strong></span><ArrowRight/></a><a href="tel:+37493700251"><Phone/><span><small>{c.phone}</small><strong>+374 93 700251</strong></span><ArrowRight/></a><a href={WHATSAPP} target="_blank" rel="noreferrer"><MessageCircle/><span><small>{c.whatsapp}</small><strong>+374 93 700251</strong></span><ExternalLink/></a><div><MessageCircle/><span><small>{c.telegram}</small><strong>+374 93 700251</strong></span><i>{s.telegramDisplay}</i></div><a className="wide" href={MAP_ADDRESS} target="_blank" rel="noreferrer"><MapPin/><span><small>{c.office}</small><strong>{c.address}</strong></span><ExternalLink/></a></div></section><Cta lang={lang} label={c.cta}/></div>}

function routeNow():DeckRoute|null{const p=window.location.pathname as DeckRoute;return ["/product","/how-it-works","/pricing","/clinical-safety","/about"].includes(p)?p:null}
function langNow():Lang{const v=localStorage.getItem("teta2-product-language")??localStorage.getItem("teta2-v4-language");return v==="hy"||v==="ru"?v:"en"}
function renderRoute(route:DeckRoute,lang:Lang){if(route==="/product")return <ProductPageDeck lang={lang}/>;if(route==="/how-it-works")return <HowPageDeck lang={lang}/>;if(route==="/pricing")return <PricingPageDeck lang={lang}/>;if(route==="/clinical-safety")return <SafetyPageDeck lang={lang}/>;return <AboutPageDeck lang={lang}/>}

export function PageDeckSectionsV2(){
  const [route,setRoute]=useState<DeckRoute|null>(()=>routeNow());
  const [lang,setLang]=useState<Lang>(()=>langNow());
  const [host,setHost]=useState<HTMLElement|null>(null);
  useEffect(()=>{const sync=()=>setRoute(routeNow());const language=(e:Event)=>{const v=(e as CustomEvent<Lang>).detail;setLang(v==="hy"||v==="ru"?v:"en")};window.addEventListener("popstate",sync);window.addEventListener("teta2-language-change",language);return()=>{window.removeEventListener("popstate",sync);window.removeEventListener("teta2-language-change",language)}},[]);
  useEffect(()=>{let observer:MutationObserver|null=null;let mountedMain:HTMLElement|null=null;let cancelled=false;document.getElementById("teta2-page-deck-v2-root")?.remove();setHost(null);if(!route)return;
    const mount=()=>{if(cancelled)return true;const main=document.querySelector<HTMLElement>(".product-marketing-page");if(!main)return false;mountedMain=main;main.classList.add("deck2-only-page");let node=document.getElementById("teta2-page-deck-v2-root") as HTMLElement|null;if(!node){node=document.createElement("div");node.id="teta2-page-deck-v2-root";main.appendChild(node)}setHost(node);return true};
    if(!mount()){observer=new MutationObserver(()=>{if(mount())observer?.disconnect()});observer.observe(document.getElementById("root")??document.body,{childList:true,subtree:true})}
    return()=>{cancelled=true;observer?.disconnect();mountedMain?.classList.remove("deck2-only-page");document.getElementById("teta2-page-deck-v2-root")?.remove()}
  },[route]);
  return route&&host?createPortal(renderRoute(route,lang),host):null;
}
