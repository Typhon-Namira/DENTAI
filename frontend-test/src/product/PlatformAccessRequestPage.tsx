import { useEffect, useState, type FormEvent } from "react";
import { ArrowRight, Building2, CalendarDays, Check, LockKeyhole, Mail, ShieldCheck } from "lucide-react";

import { errorMessage } from "../api/client";
import { platformApi, type PublicPlan } from "../api/platform";
import type { ProductLang } from "./content";

const initialForm = {
  clinic_name: "",
  requested_slug: "",
  country: "Armenia",
  city: "Yerevan",
  address: "",
  website: "",
  director_name: "",
  work_email: "",
  phone: "",
  branch_count: 1,
  dentist_count: 1,
  notes: ""
};

export function PlatformAccessRequestPage({ lang, go }: { lang: ProductLang; go: (path: string) => void }) {
  const [plan, setPlan] = useState<PublicPlan | null>(null);
  const [form, setForm] = useState(initialForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [requestId, setRequestId] = useState("");

  useEffect(() => {
    void platformApi.plan().then(setPlan).catch(() => undefined);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await platformApi.requestAccess({
        ...form,
        clinic_name: form.clinic_name.trim(),
        requested_slug: form.requested_slug.trim().toLowerCase(),
        country: form.country.trim(),
        city: form.city.trim(),
        address: form.address.trim() || undefined,
        website: form.website.trim() || undefined,
        director_name: form.director_name.trim(),
        work_email: form.work_email.trim(),
        phone: form.phone.trim(),
        notes: form.notes.trim() || undefined
      });
      setRequestId(result.id);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  const hy = lang === "hy";
  return <main className="platform-access-page">
    <section className="platform-access-story">
      <button className="product-plain platform-back" onClick={() => go("/")}>← {hy ? "Գլխավոր էջ" : "Back to Teta2"}</button>
      <span className="product-kicker">TETA2 CARE · CLINIC ACCESS</span>
      <h1>{hy ? "Դիմեք ձեր կլինիկայի Teta2 Care մուտքի համար։" : "Request Teta2 Care access for your clinic."}</h1>
      <p>{hy ? "Մեկ մասնագիտական պլան, հաստատվող վճարում և հստակ 30-օրյա մուտքի շրջան։" : "One professional plan, verified payment, and a clear fixed 30-day access period."}</p>
      <div className="platform-access-steps">
        <article><span>1</span><div><strong>{hy ? "Ուղարկել հարցումը" : "Submit request"}</strong><small>{hy ? "Կլինիկայի և տնօրենի տվյալները" : "Clinic and director details"}</small></div></article>
        <article><span>2</span><div><strong>{hy ? "Վերանայում և վճարում" : "Review & payment"}</strong><small>{hy ? "Հաստատումից հետո ստացեք վճարման տվյալները" : "Receive payment instructions after approval"}</small></div></article>
        <article><span>3</span><div><strong>{hy ? "30-օրյա ակտիվացում" : "30-day activation"}</strong><small>{hy ? "Մուտքի տվյալները ուղարկվում են էլ. փոստով" : "Credentials are emailed after payment verification"}</small></div></article>
      </div>
      <div className="platform-access-trust"><span><CalendarDays/>Exactly 30 days per paid period</span><span><LockKeyhole/>Renewal never clears clinic data</span><span><Mail/>Email notices for payment and activation</span></div>
    </section>

    <section className="platform-access-form-wrap">
      <div className="platform-plan-summary"><div><small>ONLY PLAN</small><strong>Teta2 Care</strong><span>{plan ? `${plan.price} ${plan.currency} · ${plan.subscription_days} days` : "Fixed 30-day access"}</span></div><ShieldCheck/></div>
      {requestId ? <div className="platform-request-success"><span><Check/></span><h2>{hy ? "Հարցումն ուղարկված է" : "Request submitted"}</h2><p>{hy ? "Teta2 թիմը կվերանայի հարցումը։ Հաստատվելու դեպքում վճարման հրահանգները կուղարկվեն ձեր աշխատանքային էլ. փոստին։" : "The Teta2 team will review it. If approved, payment instructions will be sent to your work email."}</p><div><small>REQUEST ID</small><strong>{requestId}</strong></div><button className="product-primary" onClick={() => go("/login")}>{hy ? "Գնալ մուտքի էջ" : "Go to clinic sign in"}<ArrowRight size={17}/></button></div> : <form className="platform-access-form" onSubmit={submit}>
        <header><span><Building2/></span><div><h2>{hy ? "Կլինիկայի մուտքի հարցում" : "Clinic access request"}</h2><p>{hy ? "Այս փուլում հաշիվ կամ գաղտնաբառ չի ստեղծվում։" : "No account or password is created until payment is verified."}</p></div></header>
        <div className="platform-form-grid">
          <label>Clinic name<input required minLength={2} maxLength={200} value={form.clinic_name} onChange={(e)=>setForm({...form,clinic_name:e.target.value})}/></label>
          <label>Requested clinic ID<input required minLength={3} maxLength={80} pattern="[a-z0-9-]+" value={form.requested_slug} onChange={(e)=>setForm({...form,requested_slug:e.target.value.toLowerCase().replace(/[^a-z0-9-]/g,"")})} placeholder="clinic-name"/></label>
          <label>Country<input required value={form.country} onChange={(e)=>setForm({...form,country:e.target.value})}/></label>
          <label>City<input required value={form.city} onChange={(e)=>setForm({...form,city:e.target.value})}/></label>
          <label>Clinic address<input value={form.address} onChange={(e)=>setForm({...form,address:e.target.value})}/></label>
          <label>Website<input type="url" value={form.website} onChange={(e)=>setForm({...form,website:e.target.value})} placeholder="https://clinic.com"/></label>
          <label>Director / owner name<input required value={form.director_name} onChange={(e)=>setForm({...form,director_name:e.target.value})}/></label>
          <label>Work email<input required type="email" value={form.work_email} onChange={(e)=>setForm({...form,work_email:e.target.value})}/></label>
          <label>Phone<input required value={form.phone} onChange={(e)=>setForm({...form,phone:e.target.value})} placeholder="+374 ..."/></label>
          <label>Branches<input required type="number" min={1} max={100} value={form.branch_count} onChange={(e)=>setForm({...form,branch_count:Number(e.target.value)})}/></label>
          <label>Dentists<input required type="number" min={1} max={1000} value={form.dentist_count} onChange={(e)=>setForm({...form,dentist_count:Number(e.target.value)})}/></label>
          <label className="full">Notes<textarea maxLength={4000} value={form.notes} onChange={(e)=>setForm({...form,notes:e.target.value})}/></label>
        </div>
        {error && <div className="product-error">{error}</div>}
        <button className="product-primary platform-submit" disabled={busy}>{busy ? "Submitting…" : "Submit access request"}<ArrowRight size={17}/></button>
      </form>}
    </section>
  </main>;
}
