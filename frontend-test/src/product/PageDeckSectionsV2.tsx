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
    product: {
      introK:"ԱՐՏԱԴՐԱՆՔԻ ՃԱՐՏԱՐԱՊԵՏՈՒԹՅՈՒՆ", introT:"Մեկ clinical loop՝ կառուցված պացիենտի, ոչ թե առանձին AI արդյունքի շուրջ։", introL:"Teta2-ը կապում է panoramic image-ը, AI-assisted possible findings-ը, clinician review-ը, patient record-ը և follow-up-ը մեկ տեսանելի workflow-ում։",
      loop:[["01","OPG-ն մտնում է patient record","Պանորամիկ պատկերը պահվում է պացիենտի հետ։"],["02","AI-assisted review","Համակարգը surface է անում possible findings՝ բժշկի քննության համար։"],["03","Բժիշկը որոշում է","Dentist-ը review է անում և context-ում confirm կամ reject է անում findings-ը։"],["04","Follow-up-ը մնում է տեսանելի","Problem/tooth-based follow-up-ը կապված է նույն patient record-ին։"]],
      recordK:"PATIENT WORKSPACE", recordT:"Օգտակար միավորը մեկ նկար չէ։ Դա պացիենտի clinical continuity-ն է։", recordL:"Workspace-ը միավորում է contact-ը, imaging-ը, review-ը, follow-up-ը և communication state-ը։",
      recordItems:[["Patient identity & contact","Պացիենտի հիմնական տվյալներ և կոնտակտ։"],["OPG history","Նախորդ panoramic images-ը պահվում են պացիենտի հետ։"],["Possible findings","AI-assisted findings-ը reviewable են, ոչ final diagnosis։"],["Review state","Unreviewed և reviewed վիճակները տարբերակվում են։"],["Follow-up timing","Scheduled կամ due աշխատանքը մնում է տեսանելի։"],["Message state","Outreach-ը ունի workflow state։"]],
      visibilityK:"ԻՆՉ Է ՏԵՍՆՈՒՄ ԿԼԻՆԻԿԱՆ", visibilityT:"Երեք operational visibility layer։", visibilityL:"Product-ը կառուցված է գործողության ենթակա վիճակների շուրջ, ոչ decorative analytics-ի։",
      visibility:[["Clinical","Ինչ image/finding է review արվում?","OPG, possible finding, review state"],["Patient","Ում է դա պատկանում?","Patient record, contact, history"],["Follow-up","Ինչն է դեռ սպասում գործողության?","Timing, message state, return"]],
      scopeK:"ԳԻՏԱԿՑՎԱԾ ՍԱՀՄԱՆ", scopeT:"Ֆոկուսը product որոշում է։", does:["OPG-centered clinical workflow","AI-assisted findings dentist review-ի համար","Patient-specific records","Clinical context-ին կապված follow-up","Message և return state visibility"], doesnt:["Ոչ autonomous diagnosis","Ոչ guaranteed detection","Ոչ unpublished accuracy %","Ոչ clinical exam replacement","Ոչ ամբողջ hospital ERP/billing suite"],
      fitK:"ՈՒՄ ՀԱՄԱՐ Է", fitT:"Լավագույն fit-ը՝ panoramic imaging օգտագործող կլինիկաներ, որոնք ուզում են ավելի հստակ follow-up loop։", fitL:"Teta2-ը առավել օգտակար է, երբ OPG, patient record և follow-up արդեն կան, բայց տարբեր tools/persons-ի միջև կտրված են։", fit:["Panoramic radiographs review անող clinics","Explicit clinician review ուզող teams","Patient-specific recall/follow-up visibility","Narrow clinical workflow նախընտրող operators"], cta:"Հարցնել clinic access"
    },
    how: {
      introK:"WORKFLOW, ՈՉ BLACK BOX", introT:"Upload-ից հետո տեղի ունեցողը նույնքան կարևոր է, որքան model output-ը։", introL:"Teta2-ը տեսանելի է պահում՝ ով է review արել, ինչ follow-up կա, outreach-ը ուղարկվել է թե ոչ և պացիենտը վերադարձել է թե ոչ։",
      steps:[["01","Create patient","Սկսեք patient identity/contact context-ից։"],["02","Upload OPG","Կցեք panoramic radiograph-ը պացիենտին։"],["03","AI-assisted analysis","Ստացեք possible findings professional review-ի համար։"],["04","Clinical review","Dentist-ը confirm/reject է անում context-ում։"],["05","Keep the record","OPG, findings և review-ը մնում են patient record-ում։"],["06","Set follow-up","Սահմանեք problem/tooth-based timing։"],["07","Send outreach","Օգտագործեք configured messaging workflow-ը։"],["08","Track return","Follow-up-ը տեսանելի է մինչև workflow-ի առաջ շարժվելը։"]],
      stateK:"STATE MACHINE", stateT:"Workflow-ը explicit states-ի շուրջ է, ոչ assumptions-ի։", stateL:"State-ը ցույց է տալիս՝ ինչ է արդեն եղել, ոչ թե ինչ պետք է ենթադրել հաջորդը։",
      states:[["UNREVIEWED","Finding-ը կա, dentist review-ը pending է։"],["REVIEWED","Finding-ը clinician-ը ուսումնասիրել է։"],["SCHEDULED","Future follow-up-ը ստեղծված է։"],["DUE","Follow-up-ը հասել է action window-ին։"],["SENDING / SENT","Outreach-ը ունի delivery state։"],["RETURN","Պացիենտը վերադառնում է workflow։"]],
      handK:"ԵՐԵՔ RESPONSIBILITY GATE", handT:"Automation-ը տեղափոխում է ինֆորմացիան։ Responsibility-ն մնում է տեսանելի։", hand:[["AI → Dentist","Model-ը surface է անում possible findings, dentist-ը clinical interpretation-ի պատասխանատուն է։"],["Dentist → Record","Review decision-ը պահվում է patient/OPG history-ի հետ։"],["Record → Patient","Follow-up outreach-ը կապված է clinical context-ի հետ։"]],
      exceptionsK:"ԵՐԲ FLOW-Ը ՉԻ ԱՎԱՐՏՎՈՒՄ", exceptionsT:"Համակարգը պետք է ցույց տա unfinished work-ը։", exceptions:[["Review incomplete","Finding-ը մնում է unreviewed։"],["Follow-up due","Մնում է due մինչև action։"],["Message sent","Sent-ը communication state է, ոչ treatment proof։"],["Patient not returned","Workflow-ը կարող է բաց մնալ։"]],
      boundaryK:"AUTOMATION BOUNDARY", boundaryT:"Չորս բան, որ Teta2-ը ինքնուրույն չի ենթադրում։", boundary:["Model output-ը definitive diagnosis չէ։","Sent message-ը completed clinical result չէ։","Follow-up state-ը silently չի փակվում։","Diagnosis/treatment decision-ը clinician-ինն է։"], cta:"Հարցնել access"
    },
    pricing: {
      introK:"CLINIC SUBSCRIPTION", introT:"Երկու շուկա։ Մեկ պարզ monthly subscription model։", introL:"Գինը մեկ clinic-ի համար է ամսական։ Funding Plan-ը սահմանափակ launch price է յուրաքանչյուր շուկայում առաջին 50 clinics-ի համար։ Availability-ն հաստատվում է access review-ի ժամանակ։",
      standard:"Standard", funding:"Funding Plan", first50:"Առաջին 50 clinics", month:"/ ամիս", marketA:"Armenia", marketR:"Russia", amdStandard:"49,000 AMD", amdFunding:"39,000 AMD", rubStandard:"14,000 RUB", rubFunding:"11,400 RUB",
      fundingK:"FUNDING PLAN", fundingT:"Launch price առաջին 50 clinics-ի համար — ոչ stripped-down product tier։", fundingL:"Funding Plan-ը early-clinic գինն է յուրաքանչյուր շուկայում առաջին 50 clinics-ի համար։ Site-ը live remaining-slot counter չի հրապարակում, ուստի availability-ն հաստատվում է access review-ում։",
      includeK:"ԻՆՉ Է ՆԵՐԱՌՎԱԾ", includeT:"Վճարվող արժեքը հենց workflow-ն է։", includeL:"Subscription-ը կառուցված է OPG review-ի, patient continuity-ի և follow-up visibility-ի շուրջ։", included:["AI-assisted OPG analysis","Possible findings dentist examination-ի համար","Visual OPG review workflow","Smart patient record","OPG/analysis history","Clinician review state","Problem/tooth-based follow-up timing","Patient messaging workflow","Follow-up dashboard visibility","Patient-return tracking"],
      fairK:"FAIR USE", fairT:"Normal clinical use-ի համար per-OPG counter չկա։", fairL:"Active subscription-ի ընթացքում OPG analysis-ը unlimited է normal clinical use-ի համար։ Fair Use-ը կիրառվում է abnormal automated bulk processing կամ API abuse-ի դեպքում։",
      onboardK:"ACCESS PROCESS", onboardT:"Clinic access-ը provision է արվում վերահսկված ձևով։", onboardL:"Public self-service provisioning-ը միացված չէ։ Access-ը request → review → activation flow ունի։", onboard:[["01","Request","Ուղարկեք clinic/contact info։"],["02","Review","Teta2-ը review է անում request-ը։"],["03","Activate","Approval-ից հետո workspace/credentials են տրվում։"],["04","Continue","Renewal-ը շարունակելու է նույն clinic workspace-ը։"]], note:"Վերևի գները Teta2-ի ներկայիս տրամադրված գներն են։ Subscription-ը չի նշանակում regulatory կամ diagnostic guarantee։", cta:"Հարցնել access"
    },
    safety: {
      introK:"CLINICAL SAFETY", introT:"Safety-ն սկսվում է այն claims-ից, որոնք product-ը չի անում։", introL:"Teta2-ը ներկայացնում է AI-assisted possible findings dentist examination-ի համար։ Model output-ը definitive diagnosis չի ներկայացվում և unpublished accuracy claim չի արվում։",
      claimsK:"CLAIMS BOUNDARY", claimsT:"Responsible language-ը decision boundary-ն հստակ է պահում։", safe:["Possible finding","AI-assisted analysis","Requires dentist examination","Clinician reviewed / unreviewed","Follow-up scheduled / due"], unsafe:["AI-only definitive diagnosis","Guaranteed detection","Guaranteed clinical outcome","Unpublished accuracy %","Message sent = treatment completed"],
      humanK:"HUMAN IN THE LOOP", humanT:"AI-ը surface է անում ինֆորմացիան։ Decision gate-ը clinician-ինն է։", humanL:"WHO AI-for-health guidance-ը շեշտում է ethics, accountability և appropriate human oversight-ը։ Teta2-ը model output-ը պահում է reviewable, ոչ autonomous։", human:[["01","AI-assisted output"],["02","Dentist examination"],["03","Confirm / reject"],["04","Follow-up / care decision"]],
      imagingK:"IMAGING CONTEXT", imagingT:"OPG-ն clinical evidence է, ոչ ամբողջ clinical examination-ը։", imagingL:"ADA/AAOMR guidance-ը շեշտում է clinical examination-ը և patient-specific need-ը radiographic imaging-ի օգտագործման ժամանակ։",
      opsK:"OPERATIONAL HONESTY", opsT:"Interface-ը տարբերակում է այն, ինչ եղել է, նրանից, ինչ դեռ սպասվում է։", ops:[["Finding exists","Diagnosis complete չի նշանակում։"],["Clinician reviewed","Treatment occurred չի նշանակում։"],["Message sent","Patient returned չի նշանակում։"],["Follow-up due","Clinic acted չի նշանակում։"]], foot:"Teta2-ը clinical decision-support workflow է։ Professional examination և dentist responsibility-ը մնում են անհրաժեշտ։", source:"Կարդալ աղբյուրը", cta:"Հարցնել access"
    },
    about: {
      introK:"TETA2-Ի ՄԱՍԻՆ", introT:"Ֆոկուսավորված dental AI նախագիծ՝ կառուցվող Երևանում։", introL:"Teta2-ը կառուցվում է մեկ նեղ operational խնդրի շուրջ՝ OPG review-ը կապել patient record-ի և visible follow-up workflow-ի հետ։ Site-ը ներկայացնում է այն որպես pre-incorporation software project, ոչ regulatory approval claim։",
      principle:"Radiograph-ը չպետք է դառնա isolated AI result։ Այն պետք է կապված մնա clinician-ի, patient-ի և next action-ի հետ։",
      teamK:"ԹԻՄ", teamT:"Նախագծի հետ ներկայում նույնականացված մարդիկ։", teamL:"Roles-ը դիտավորյալ narrow/factual են։ Public links-ը տրված են այնտեղ, որտեղ կան։", typhonRole:"Founder · Teta2", vanRole:"Co-founder · Technical / AI model fine-tuning",
      typhonExperience:[["PulseMeal","Founder experience՝ Yerevan-ում AR + AI restaurant technology startup կառուցելու մեջ։"],["FinnoWay Armenia 2025","PulseMeal-ը publicly ներկայացվել է Startup Alley-ում Երևանում։"],["Founders Event Horizon · 2026","Yerevan-ում publicly organized founder-networking activity startups/entrepreneurship թեմայով։"]], vanBody:"Van Arzoyan-ը աշխատել է Teta2-ի technical մասի վրա, ներառյալ AI model fine-tuning-ը։", publicProfile:"Public profile", publicSource:"Public source",
      buildK:"ԻՆՉՊԵՍ Է ԿԱՌՈՒՑՎՈՒՄ PROJECT-Ը", buildT:"Narrow scope, visible states և պաշտպանելի claims։", build:[["01","Start with the OPG","Մեկ imaging workflow-ը պահել կենտրոնում։"],["02","Keep the dentist in control","Possible findings-ը reviewable են, clinical decision-ը dentist-ինն է։"],["03","Connect follow-up","Analysis-ից հետո patient-specific follow-up state։"],["04","Avoid fake proof","Ոչ invented customer count, accuracy %, revenue կամ clinical outcome։"]],
      contactK:"ԿԱՊ", contactT:"Կապվեք անմիջապես Teta2 թիմի հետ։", contactL:"Clinic access-ի, product հարցերի, technical discussion-ի կամ partnership-ի համար ընտրեք հարմար channel-ը։", email:"Email", phone:"Հեռախոս", whatsapp:"WhatsApp", telegram:"Telegram", office:"Գրասենյակ", address:"4 Arshakunyats Avenue, Yerevan 0023, Armenia", cta:"Հարցնել clinic access"
    }
  },
  ru: {
    product: {
      introK:"АРХИТЕКТУРА ПРОДУКТА", introT:"Один clinical loop вокруг пациента, а не вокруг отдельного AI-результата.", introL:"Teta2 связывает панорамный снимок, AI-assisted possible findings, review врача, patient record и follow-up в один видимый workflow.",
      loop:[["01","OPG входит в карту пациента","Панорамный снимок хранится с пациентом, а не как отдельная загрузка."],["02","AI-assisted review","Система показывает possible findings для оценки стоматологом."],["03","Решение врача","Стоматолог оценивает finding в контексте и подтверждает или отклоняет его."],["04","Follow-up остается видимым","Problem/tooth-based follow-up связан с тем же patient record."]],
      recordK:"PATIENT WORKSPACE", recordT:"Полезная единица — не один снимок, а клиническая непрерывность пациента.", recordL:"Workspace связывает контакт, imaging, review, follow-up и communication state.", recordItems:[["Patient identity & contact","Базовые данные и контакт пациента."],["OPG history","Предыдущие панорамные снимки связаны с пациентом."],["Possible findings","AI-assisted findings остаются reviewable, а не final diagnosis."],["Review state","Unreviewed и reviewed состояния различимы."],["Follow-up timing","Scheduled/due работа остается видимой."],["Message state","Outreach имеет явный workflow state."]],
      visibilityK:"ЧТО ВИДИТ КЛИНИКА", visibilityT:"Три уровня operational visibility.", visibilityL:"Продукт строится вокруг наблюдаемых состояний, а не декоративной аналитики.", visibility:[["Clinical","Какой image/finding сейчас review?","OPG, finding, review state"],["Patient","Кому это относится?","Patient record, contact, history"],["Follow-up","Что еще ждет действия?","Timing, message state, return"]],
      scopeK:"ОСОЗНАННЫЙ SCOPE", scopeT:"Фокус — продуктовое решение.", does:["OPG-centered clinical workflow","AI-assisted findings для review врача","Patient-specific records","Follow-up в clinical context","Message/return visibility"], doesnt:["Не autonomous diagnosis","Не guaranteed detection","Не unpublished accuracy %","Не замена clinical examination","Не полный hospital ERP/billing suite"],
      fitK:"ДЛЯ КОГО", fitT:"Лучший fit — клиники с panoramic imaging, которым нужен более четкий follow-up loop.", fitL:"Teta2 полезен, когда OPG, patient record и follow-up уже существуют, но разделены между людьми и инструментами.", fit:["Клиники, работающие с panoramic radiographs","Команды с explicit clinician review","Клиники с patient-specific recall/follow-up","Операторы, предпочитающие узкий clinical workflow generic CRM"], cta:"Запросить доступ"
    },
    how: {
      introK:"WORKFLOW, А НЕ BLACK BOX", introT:"То, что происходит после upload, так же важно, как model output.", introL:"Teta2 делает видимыми review, follow-up, outreach и return пациента.",
      steps:[["01","Create patient","Начните с identity/contact context пациента."],["02","Upload OPG","Прикрепите panoramic radiograph к пациенту."],["03","AI-assisted analysis","Получите possible findings для professional review."],["04","Clinical review","Стоматолог confirm/reject findings в контексте."],["05","Keep the record","OPG/findings/review остаются в patient record."],["06","Set follow-up","Создайте problem/tooth-based timing."],["07","Send outreach","Используйте configured messaging workflow."],["08","Track return","Follow-up видим до движения workflow дальше."]],
      stateK:"STATE MACHINE", stateT:"Workflow строится на explicit states, а не предположениях.", stateL:"State показывает, что уже произошло, и не делает вид, что следующий шаг завершен.", states:[["UNREVIEWED","Finding есть, review врача pending."],["REVIEWED","Finding оценен clinician."],["SCHEDULED","Future follow-up создан."],["DUE","Follow-up достиг action window."],["SENDING / SENT","Outreach имеет delivery state."],["RETURN","Пациент возвращается в workflow."]],
      handK:"ТРИ RESPONSIBILITY GATE", handT:"Automation переносит информацию. Responsibility остается видимой.", hand:[["AI → Dentist","Model surfaces possible findings; dentist отвечает за clinical interpretation."],["Dentist → Record","Review decision хранится с patient/OPG history."],["Record → Patient","Follow-up outreach связан с clinical context."]],
      exceptionsK:"ЕСЛИ FLOW НЕ ЗАВЕРШЕН", exceptionsT:"Система должна показывать unfinished work.", exceptions:[["Review incomplete","Finding остается unreviewed."],["Follow-up due","Остается due до действия."],["Message sent","Sent — communication state, не proof of treatment."],["Patient not returned","Workflow может оставаться open."]],
      boundaryK:"AUTOMATION BOUNDARY", boundaryT:"Четыре вещи, которые Teta2 не предполагает автоматически.", boundary:["Model output не definitive diagnosis.","Sent message не completed clinical result.","Follow-up state не закрывается silently.","Diagnosis/treatment decision остается за clinician."], cta:"Запросить доступ"
    },
    pricing: {
      introK:"CLINIC SUBSCRIPTION", introT:"Два рынка. Одна понятная monthly subscription model.", introL:"Цена указана за одну clinic в месяц. Funding Plan — ограниченная launch price для первых 50 clinics в каждом рынке; availability подтверждается при access review.",
      standard:"Standard", funding:"Funding Plan", first50:"Первые 50 clinics", month:"/ месяц", marketA:"Armenia", marketR:"Russia", amdStandard:"49,000 AMD", amdFunding:"39,000 AMD", rubStandard:"14,000 RUB", rubFunding:"11,400 RUB",
      fundingK:"FUNDING PLAN", fundingT:"Launch price для первых 50 clinics — не урезанный product tier.", fundingL:"Funding Plan — early-clinic цена для первых 50 clinics в каждом рынке. Сайт не публикует live remaining-slot counter, поэтому availability подтверждается в access review.",
      includeK:"ЧТО ВХОДИТ", includeT:"Оплачивается сам рабочий workflow.", includeL:"Subscription строится вокруг OPG review, patient continuity и follow-up visibility.", included:["AI-assisted OPG analysis","Possible findings для dentist examination","Visual OPG review workflow","Smart patient record","OPG/analysis history","Clinician review state","Problem/tooth follow-up timing","Patient messaging workflow","Follow-up dashboard visibility","Patient-return tracking"],
      fairK:"FAIR USE", fairT:"Для normal clinical use нет per-OPG counter.", fairL:"В active subscription OPG analysis unlimited для normal clinical use. Fair Use применяется к abnormal automated bulk processing или API abuse.",
      onboardK:"ACCESS PROCESS", onboardT:"Clinic access provisioned намеренно.", onboardL:"Public self-service provisioning не включен. Access проходит request → review → activation.", onboard:[["01","Request","Отправьте clinic/contact info."],["02","Review","Teta2 review заявки."],["03","Activate","После approval выдаются workspace/credentials."],["04","Continue","Renewal продолжает тот же clinic workspace."]], note:"Цены выше — текущие цены Teta2. Subscription не является regulatory или diagnostic guarantee.", cta:"Запросить доступ"
    },
    safety: {
      introK:"CLINICAL SAFETY", introT:"Safety начинается с claims, которые продукт отказывается делать.", introL:"Teta2 показывает AI-assisted possible findings для dentist examination. Model output не выдается за definitive diagnosis, unpublished accuracy claim не публикуется.",
      claimsK:"CLAIMS BOUNDARY", claimsT:"Responsible language сохраняет ясную границу решения.", safe:["Possible finding","AI-assisted analysis","Requires dentist examination","Clinician reviewed / unreviewed","Follow-up scheduled / due"], unsafe:["AI-only definitive diagnosis","Guaranteed detection","Guaranteed clinical outcome","Unpublished accuracy %","Message sent = treatment completed"],
      humanK:"HUMAN IN THE LOOP", humanT:"AI показывает информацию. Decision gate остается за clinician.", humanL:"WHO guidance по AI for health подчеркивает ethics, accountability и human oversight. Teta2 сохраняет model output reviewable, а не autonomous.", human:[["01","AI-assisted output"],["02","Dentist examination"],["03","Confirm / reject"],["04","Follow-up / care decision"]],
      imagingK:"IMAGING CONTEXT", imagingT:"OPG — clinical evidence, но не весь clinical examination.", imagingL:"ADA/AAOMR guidance подчеркивает clinical examination и patient-specific need при использовании radiographic imaging.",
      opsK:"OPERATIONAL HONESTY", opsT:"Интерфейс различает то, что произошло, и то, что только ожидается.", ops:[["Finding exists","Не означает diagnosis complete."],["Clinician reviewed","Не означает treatment occurred."],["Message sent","Не означает patient returned."],["Follow-up due","Не означает clinic acted."]], foot:"Teta2 — clinical decision-support workflow. Professional examination и dentist responsibility остаются необходимыми.", source:"Открыть источник", cta:"Запросить доступ"
    },
    about: {
      introK:"О TETA2", introT:"Фокусированный dental AI проект, создаваемый в Ереване.", introL:"Teta2 строится вокруг одной operational задачи: связать OPG review с patient record и visible follow-up workflow. Сайт представляет проект как pre-incorporation software project, а не regulatory approval claim.",
      principle:"Radiograph не должен становиться isolated AI result. Он должен оставаться связанным с clinician, patient и next action.",
      teamK:"КОМАНДА", teamT:"Люди, которые сейчас указаны в проекте.", teamL:"Roles намеренно описаны узко и фактически. Public-source links добавлены там, где они есть.", typhonRole:"Founder · Teta2", vanRole:"Co-founder · Technical / AI model fine-tuning",
      typhonExperience:[["PulseMeal","Founder experience в создании AR + AI restaurant technology startup в Ереване."],["FinnoWay Armenia 2025","PulseMeal публично участвовал в Startup Alley в Ереване."],["Founders Event Horizon · 2026","Публично организованная founder-networking activity в Ереване вокруг startups и entrepreneurship."]], vanBody:"Van Arzoyan работал над technical частью Teta2, включая AI model fine-tuning.", publicProfile:"Public profile", publicSource:"Public source",
      buildK:"КАК СТРОИТСЯ ПРОЕКТ", buildT:"Narrow scope, visible states и claims, которые можно защитить.", build:[["01","Start with the OPG","Один imaging workflow остается в центре."],["02","Keep the dentist in control","Possible findings reviewable, clinical decision за dentist."],["03","Connect follow-up","После analysis остается patient-specific follow-up state."],["04","Avoid fake proof","Нет invented customer count, accuracy %, revenue или clinical outcome."]],
      contactK:"КОНТАКТ", contactT:"Свяжитесь напрямую с командой Teta2.", contactL:"Для clinic access, product вопросов, technical discussion или partnerships используйте удобный канал.", email:"Email", phone:"Телефон", whatsapp:"WhatsApp", telegram:"Telegram", office:"Офис", address:"4 Arshakunyats Avenue, Yerevan 0023, Armenia", cta:"Запросить clinic access"
    }
  }
} as const;

function Heading({kicker,title,lead}:{kicker:string;title:string;lead?:string}){return <header className="deck2-heading"><span><Sparkles size={14}/>{kicker}</span><h2>{title}</h2>{lead&&<p>{lead}</p>}</header>}
function Cta({label}:{label:string}){return <div className="deck2-cta"><div><b>Teta2</b><span>OPG intelligence + patient follow-up</span></div><a href="/register">{label}<ArrowRight/></a></div>}

function ProductPageDeck({lang}:{lang:Lang}){const c=COPY[lang].product;return <div className="deck2 deck2-product">
<section className="deck2-section deck2-intro"><Heading kicker={c.introK} title={c.introT} lead={c.introL}/><div className="deck2-loop">{c.loop.map(([n,t,b],i)=><article key={n}><span>{n}</span><div><strong>{t}</strong><p>{b}</p></div>{i<c.loop.length-1&&<ArrowRight/>}</article>)}</div></section>
<section className="deck2-section deck2-record"><Heading kicker={c.recordK} title={c.recordT} lead={c.recordL}/><div className="deck2-record-shell"><div className="deck2-record-spine"><UserRoundCheck/><b>Patient</b><span>Clinical continuity</span></div><div className="deck2-record-grid">{c.recordItems.map(([t,b],i)=><article key={t}><small>0{i+1}</small><strong>{t}</strong><p>{b}</p></article>)}</div></div></section>
<section className="deck2-section deck2-visibility"><Heading kicker={c.visibilityK} title={c.visibilityT} lead={c.visibilityL}/><div className="deck2-visibility-stage">{c.visibility.map(([t,q,a],i)=><article key={t} className={`v${i+1}`}><span>{i===0?<Radar/>:i===1?<FolderHeart/>:<HeartPulse/>}</span><small>{t}</small><h3>{q}</h3><p>{a}</p></article>)}</div></section>
<section className="deck2-section deck2-scope"><Heading kicker={c.scopeK} title={c.scopeT}/><div className="deck2-scope-grid"><article><h3><CheckCircle2/>{lang==="en"?"Built to":"Teta2"}</h3>{c.does.map(x=><p key={x}><Check/>{x}</p>)}</article><article><h3><ShieldCheck/>{lang==="en"?"Not built to":"Scope"}</h3>{c.doesnt.map(x=><p key={x}><span>×</span>{x}</p>)}</article></div></section>
<section className="deck2-section deck2-fit"><Heading kicker={c.fitK} title={c.fitT} lead={c.fitL}/><div className="deck2-fit-grid">{c.fit.map((x,i)=><article key={x}><b>0{i+1}</b><p>{x}</p></article>)}</div></section><Cta label={c.cta}/></div>}

function HowPageDeck({lang}:{lang:Lang}){const c=COPY[lang].how;return <div className="deck2 deck2-how">
<section className="deck2-section"><Heading kicker={c.introK} title={c.introT} lead={c.introL}/><div className="deck2-workflow-spine">{c.steps.map(([n,t,b])=><article key={n}><span>{n}</span><div><strong>{t}</strong><p>{b}</p></div></article>)}</div></section>
<section className="deck2-section deck2-state"><Heading kicker={c.stateK} title={c.stateT} lead={c.stateL}/><div className="deck2-state-board">{c.states.map(([t,b],i)=><article key={t}><i>{i+1}</i><strong>{t}</strong><p>{b}</p></article>)}</div></section>
<section className="deck2-section deck2-handoff"><Heading kicker={c.handK} title={c.handT}/><div className="deck2-handoff-flow">{c.hand.map(([t,b],i)=><article key={t}><span>{i===0?<BrainCircuit/>:i===1?<FolderHeart/>:<MessageCircle/>}</span><strong>{t}</strong><p>{b}</p></article>)}</div></section>
<section className="deck2-section deck2-exception"><Heading kicker={c.exceptionsK} title={c.exceptionsT}/><div className="deck2-exception-list">{c.exceptions.map(([t,b],i)=><article key={t}><b>0{i+1}</b><div><strong>{t}</strong><p>{b}</p></div></article>)}</div></section>
<section className="deck2-section deck2-boundary"><Heading kicker={c.boundaryK} title={c.boundaryT}/><div className="deck2-boundary-row">{c.boundary.map((x,i)=><article key={x}><CircleAlert/><span>0{i+1}</span><p>{x}</p></article>)}</div></section><Cta label={c.cta}/></div>}

function PricingPageDeck({lang}:{lang:Lang}){const c=COPY[lang].pricing;return <div className="deck2 deck2-pricing">
<section className="deck2-section"><Heading kicker={c.introK} title={c.introT} lead={c.introL}/><div className="deck2-market-stage"><article className="armenia"><header><span>AM</span><strong>{c.marketA}</strong></header><div className="deck2-price-row"><div><small>{c.standard}</small><b>{c.amdStandard}</b><span>{c.month}</span></div><ArrowRight/><div className="fund"><small>{c.funding} · {c.first50}</small><b>{c.amdFunding}</b><span>{c.month}</span></div></div></article><article className="russia"><header><span>RU</span><strong>{c.marketR}</strong></header><div className="deck2-price-row"><div><small>{c.standard}</small><b>{c.rubStandard}</b><span>{c.month}</span></div><ArrowRight/><div className="fund"><small>{c.funding} · {c.first50}</small><b>{c.rubFunding}</b><span>{c.month}</span></div></div></article></div></section>
<section className="deck2-section deck2-funding"><Heading kicker={c.fundingK} title={c.fundingT} lead={c.fundingL}/><div className="deck2-50"><strong>50</strong><span>{c.first50}</span><div>{Array.from({length:10},(_,i)=><i key={i}/>)}</div></div></section>
<section className="deck2-section"><Heading kicker={c.includeK} title={c.includeT} lead={c.includeL}/><div className="deck2-inclusions">{c.included.map((x,i)=><article key={x}><span>{i<3?<FileImage/>:i<6?<FolderHeart/>:<HeartPulse/>}</span><p>{x}</p><Check/></article>)}</div></section>
<section className="deck2-section deck2-fair"><Heading kicker={c.fairK} title={c.fairT} lead={c.fairL}/><div className="deck2-infinity"><Activity/><b>∞</b><span>NORMAL CLINICAL USE</span></div></section>
<section className="deck2-section"><Heading kicker={c.onboardK} title={c.onboardT} lead={c.onboardL}/><div className="deck2-onboard">{c.onboard.map(([n,t,b])=><article key={n}><span>{n}</span><strong>{t}</strong><p>{b}</p></article>)}</div><p className="deck2-note"><CircleAlert/>{c.note}</p></section><Cta label={c.cta}/></div>}

function SafetyPageDeck({lang}:{lang:Lang}){const c=COPY[lang].safety;return <div className="deck2 deck2-safety">
<section className="deck2-section"><Heading kicker={c.introK} title={c.introT} lead={c.introL}/><div className="deck2-safety-signal"><ShieldCheck/><span>AI supports the dentist</span><b>≠</b><span>AI replaces the dentist</span></div></section>
<section className="deck2-section"><Heading kicker={c.claimsK} title={c.claimsT}/><div className="deck2-claims"><article className="safe"><h3><CheckCircle2/>Responsible</h3>{c.safe.map(x=><p key={x}><Check/>{x}</p>)}</article><article className="guard"><h3><CircleAlert/>Not without evidence</h3>{c.unsafe.map(x=><p key={x}><span>×</span>{x}</p>)}</article></div></section>
<section className="deck2-section"><Heading kicker={c.humanK} title={c.humanT} lead={c.humanL}/><div className="deck2-human-gate">{c.human.map(([n,t],i)=><article key={n}><b>{n}</b><span>{t}</span>{i<c.human.length-1&&<ArrowRight/>}</article>)}</div><a className="deck2-source" href={WHO_AI} target="_blank" rel="noreferrer">WHO · Ethics and governance of AI for health <ExternalLink/></a></section>
<section className="deck2-section deck2-imaging"><Heading kicker={c.imagingK} title={c.imagingT} lead={c.imagingL}/><div className="deck2-imaging-visual"><Stethoscope/><div/><Radar/></div><a className="deck2-source" href={ADA_RADIOGRAPHS} target="_blank" rel="noreferrer">{c.source} · ADA / AAOMR <ExternalLink/></a></section>
<section className="deck2-section"><Heading kicker={c.opsK} title={c.opsT}/><div className="deck2-ops">{c.ops.map(([a,b],i)=><article key={a}><b>0{i+1}</b><strong>{a}</strong><ArrowRight/><p>{b}</p></article>)}</div><p className="deck2-note"><ShieldCheck/>{c.foot}</p></section><Cta label={c.cta}/></div>}

function AboutPageDeck({lang}:{lang:Lang}){const c=COPY[lang].about;return <div className="deck2 deck2-about">
<section className="deck2-section deck2-about-intro"><Heading kicker={c.introK} title={c.introT} lead={c.introL}/><blockquote>{c.principle}</blockquote></section>
<section className="deck2-section"><Heading kicker={c.teamK} title={c.teamT} lead={c.teamL}/><div className="deck2-team"><article id="typhon-namira"><div className="deck2-person-head"><span>TN</span><div><small>{c.typhonRole}</small><h3>Typhon Namira</h3></div></div><div className="deck2-experience">{c.typhonExperience.map(([t,b],i)=><div key={t}><b>0{i+1}</b><span><strong>{t}</strong><p>{b}</p></span></div>)}</div><div className="deck2-links"><a href={TYPHON_LINKEDIN} target="_blank" rel="noreferrer">{c.publicProfile}<ExternalLink/></a><a href={PULSEMEAL_ABOUT} target="_blank" rel="noreferrer">{c.publicSource}<ExternalLink/></a><a href={PULSEMEAL_HOME} target="_blank" rel="noreferrer">PulseMeal<ExternalLink/></a></div></article><article id="van-arzoyan"><div className="deck2-person-head"><span>VA</span><div><small>{c.vanRole}</small><h3>Van Arzoyan</h3></div></div><div className="deck2-tech-focus"><BrainCircuit/><strong>AI model fine-tuning</strong><p>{c.vanBody}</p></div></article></div></section>
<section className="deck2-section"><Heading kicker={c.buildK} title={c.buildT}/><div className="deck2-build">{c.build.map(([n,t,b])=><article key={n}><span>{n}</span><strong>{t}</strong><p>{b}</p></article>)}</div></section>
<section className="deck2-section deck2-contact"><Heading kicker={c.contactK} title={c.contactT} lead={c.contactL}/><div className="deck2-contact-grid"><a href="mailto:teta2support@gmail.com"><Mail/><span><small>{c.email}</small><strong>teta2support@gmail.com</strong></span><ArrowRight/></a><a href="tel:+37493700251"><Phone/><span><small>{c.phone}</small><strong>+374 93 700251</strong></span><ArrowRight/></a><a href={WHATSAPP} target="_blank" rel="noreferrer"><MessageCircle/><span><small>{c.whatsapp}</small><strong>+374 93 700251</strong></span><ExternalLink/></a><div><MessageCircle/><span><small>{c.telegram}</small><strong>+374 93 700251</strong></span><i>Telegram</i></div><a className="wide" href={MAP_ADDRESS} target="_blank" rel="noreferrer"><MapPin/><span><small>{c.office}</small><strong>{c.address}</strong></span><ExternalLink/></a></div></section><Cta label={c.cta}/></div>}

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
