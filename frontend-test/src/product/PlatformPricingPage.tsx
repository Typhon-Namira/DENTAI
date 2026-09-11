import { ArrowRight, CalendarDays, Check, HeartPulse, LockKeyhole, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { platformApi, type PublicPlan } from "../api/platform";
import type { ProductLang } from "./content";

export function PlatformPricingPage({ lang, go }: { lang: ProductLang; go: (path: string) => void }) {
  const [plan, setPlan] = useState<PublicPlan | null>(null);
  useEffect(() => { void platformApi.plan().then(setPlan).catch(() => undefined); }, []);
  const hy = lang === "hy";
  return <main className="single-pricing-page">
    <button className="product-plain platform-back" onClick={() => go("/")}>← {hy ? "Գլխավոր էջ" : "Back to Teta2"}</button>
    <header><span className="product-kicker">ONE PLAN · TETA2 CARE</span><h1>{hy ? "Մեկ ամբողջական բաժանորդագրություն կլինիկայի համար։" : "One complete clinic subscription."}</h1><p>{hy ? "OPG վերլուծություն, կլինիկական պատմություն, follow-up, WhatsApp workflow և appointment coordination՝ մեկ 30-օրյա պլանում։" : "OPG intelligence, clinical history, follow-up, WhatsApp workflow and appointment coordination in one fixed 30-day plan."}</p></header>
    <article className="single-price-card">
      <div className="single-price-head"><span><HeartPulse/></span><div><small>COMPLETE CLINIC ACCESS</small><h2>Teta2 Care</h2><p>Clinical intelligence → follow-up → patient return</p></div></div>
      <div className="single-price-value"><strong>{plan ? `${plan.price} ${plan.currency}` : "Teta2 Care"}</strong><span>/ 30 days</span></div>
      <div className="single-price-features"><span><Check/>AI-assisted OPG analysis and review</span><span><Check/>Smart patient files and longitudinal history</span><span><Check/>Tooth-level follow-up plans</span><span><Check/>Clinic WhatsApp outreach and staged conversations</span><span><Check/>Appointment proposal and doctor approval flow</span><span><Check/>Dashboard, patient and operational tools</span></div>
      <div className="single-price-policy"><CalendarDays/><div><strong>Exactly 30 days per paid access period</strong><p>Renewal extends access by another 30 days. Existing clinical and patient data is retained and never reset by expiry or renewal.</p></div></div>
      <button className="product-primary" onClick={() => go("/register")}>{hy ? "Մուտքի հարցում" : "Request Teta2 Care access"}<ArrowRight size={18}/></button>
    </article>
    <div className="single-price-trust"><span><ShieldCheck/>Admin-verified activation</span><span><LockKeyhole/>Tenant-isolated clinic data</span></div>
  </main>;
}
