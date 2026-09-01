import { useEffect, useState, type FormEvent } from "react";
import { api, clearSession, errorMessage } from "../api/client";
import type { CurrentUser } from "../api/types";

type PublicView = "landing" | "login" | "register";

interface PublicPortalProps {
  onAuthenticated: (user: CurrentUser) => void;
}

const features = [
  {
    kicker: "OPG Intelligence",
    title: "از یک OPG تا یک پرونده‌ی هوشمند دندان‌به‌دندان",
    copy: "Teta2 یافته‌های مدل‌های بینایی را به یک نمای قابل‌مرور برای دندانپزشک تبدیل می‌کند؛ تصمیم نهایی همیشه با پزشک است.",
    icon: "✦"
  },
  {
    kicker: "Smart Recall",
    title: "ویزیت بعدی را از دست ندهید",
    copy: "ریسک، مراقبت آینده و Follow-up در پرونده بیمار باقی می‌مانند و جریان Outreach برای بازگرداندن بیمار به کلینیک آماده است.",
    icon: "↻"
  },
  {
    kicker: "Radar AI",
    title: "تقاضای واقعی خدمات دندانپزشکی را زودتر ببینید",
    copy: "Patient Radar فرصت‌های بالقوه را از منابع اجتماعی ثبت و رتبه‌بندی می‌کند تا تیم کلینیک بتواند آن‌ها را بررسی و پیگیری کند.",
    icon: "⌁"
  }
];

export function PublicPortal({ onAuthenticated }: PublicPortalProps) {
  const [view, setView] = useState<PublicView>("landing");
  const [clinicSlug, setClinicSlug] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState<"checking" | "online" | "offline">("checking");
  const [registrationSent, setRegistrationSent] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([api.health(controller.signal), api.ready(controller.signal)])
      .then(() => setHealth("online"))
      .catch(() => setHealth("offline"));
    return () => controller.abort();
  }, []);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.login({ clinic_slug: clinicSlug.trim().toLowerCase(), identifier: identifier.trim(), password });
      const user = await api.me();
      setPassword("");
      onAuthenticated(user);
    } catch (reason) {
      clearSession();
      setPassword("");
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  function submitRegistration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRegistrationSent(true);
  }

  if (view === "login") {
    return (
      <main className="teta-auth-shell">
        <button className="teta-back-link" type="button" onClick={() => setView("landing")}>← بازگشت به Teta2</button>
        <section className="teta-auth-story">
          <div className="teta-logo-lockup"><span className="teta-tooth-mark">T2</span><strong>Teta2</strong></div>
          <p className="teta-kicker">Teeth Evaluation & Treatment AI Assistant</p>
          <h1>کلینیک شما، با یک لایه‌ی هوشمند بالینی.</h1>
          <p>به داشبورد امن کلینیک وارد شوید، OPG را تحلیل کنید، پرونده دندان‌ها را در طول زمان نگه دارید و فرصت‌های Radar AI را بررسی کنید.</p>
          <div className="teta-auth-points">
            <span>۹ مدل ONNX برای تحلیل OPG</span>
            <span>Clinician review قبل از نهایی‌سازی یافته‌ها</span>
            <span>Private X-ray storage و Tenant isolation</span>
          </div>
        </section>
        <section className="teta-auth-card">
          <div>
            <span className={`teta-live-chip ${health}`}>{health === "online" ? "Backend online" : health === "checking" ? "Checking backend" : "Backend unavailable"}</span>
            <h2>ورود به داشبورد</h2>
            <p>Clinic slug، ایمیل یا نام کاربری و رمز عبور خود را وارد کنید.</p>
          </div>
          <form onSubmit={submitLogin}>
            <label>Clinic slug<input required minLength={2} maxLength={80} pattern="[a-z0-9-]+" placeholder="marstom" value={clinicSlug} onChange={(e) => setClinicSlug(e.target.value.toLowerCase())} /></label>
            <label>ایمیل یا نام کاربری<input required autoComplete="username" placeholder="doctor@clinic.com" value={identifier} onChange={(e) => setIdentifier(e.target.value)} /></label>
            <label>رمز عبور<input required type="password" autoComplete="current-password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} /></label>
            {error && <div className="teta-auth-error" role="alert">{error}</div>}
            <button className="teta-primary-button" type="submit" disabled={busy}>{busy ? "در حال ورود…" : "ورود امن"}</button>
          </form>
          <p className="teta-auth-switch">هنوز کلینیک شما در Teta2 فعال نشده؟ <button type="button" onClick={() => setView("register")}>درخواست فعال‌سازی</button></p>
        </section>
      </main>
    );
  }

  if (view === "register") {
    return (
      <main className="teta-auth-shell registration-shell">
        <button className="teta-back-link" type="button" onClick={() => setView("landing")}>← بازگشت به Teta2</button>
        <section className="teta-auth-story">
          <div className="teta-logo-lockup"><span className="teta-tooth-mark">T2</span><strong>Teta2</strong></div>
          <p className="teta-kicker">Clinic onboarding</p>
          <h1>کلینیک خود را برای Teta2 آماده کنید.</h1>
          <p>برای هر کلینیک یک tenant database مجزا ساخته می‌شود؛ به همین دلیل فعال‌سازی کلینیک یک مرحله provisioning امن دارد و در نسخه فعلی فوراً از مرورگر انجام نمی‌شود.</p>
          <div className="teta-auth-points"><span>Database مجزا برای داده‌های بالینی</span><span>Branch و Director account در onboarding ساخته می‌شوند</span><span>دامنه کلینیک به CORS allowlist اضافه می‌شود</span></div>
        </section>
        <section className="teta-auth-card">
          <div><span className="teta-live-chip preview">Onboarding request</span><h2>درخواست ثبت کلینیک</h2><p>فرم رابط کاربری آماده است؛ endpoint ثبت self-service در بک‌اند فعلی وجود ندارد و در مرحله backend onboarding به آن متصل می‌شود.</p></div>
          {registrationSent ? (
            <div className="teta-registration-success"><span>✓</span><h3>فرم آماده است</h3><p>برای فعال شدن واقعی، مرحله provisioning دیتابیس کلینیک و endpoint onboarding را در بک‌اند اضافه می‌کنیم.</p><button className="teta-primary-button" type="button" onClick={() => setView("login")}>رفتن به ورود</button></div>
          ) : (
            <form onSubmit={submitRegistration}>
              <div className="teta-form-grid"><label>نام کلینیک<input required placeholder="Marstom Clinic" /></label><label>شهر<input required placeholder="Yerevan" /></label></div>
              <div className="teta-form-grid"><label>نام مدیر<input required placeholder="David Gevorgyan" /></label><label>ایمیل کاری<input required type="email" placeholder="director@clinic.com" /></label></div>
              <label>نام پیشنهادی Clinic slug<input required pattern="[a-z0-9-]+" placeholder="marstom" /></label>
              <label>تعداد شعبه<select defaultValue="1"><option value="1">۱ شعبه</option><option value="2-3">۲ تا ۳ شعبه</option><option value="4+">۴ شعبه یا بیشتر</option></select></label>
              <button className="teta-primary-button" type="submit">ادامه فرایند فعال‌سازی</button>
            </form>
          )}
          <p className="teta-auth-switch">کلینیک از قبل فعال است؟ <button type="button" onClick={() => setView("login")}>ورود</button></p>
        </section>
      </main>
    );
  }

  return (
    <main className="teta-public-site">
      <header className="teta-public-nav">
        <button className="teta-logo-lockup" type="button" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}><span className="teta-tooth-mark">T2</span><strong>Teta2</strong></button>
        <nav><a href="#product">محصول</a><a href="#radar">Radar AI</a><a href="#workflow">نحوه کار</a><a href="#security">امنیت</a></nav>
        <div className="teta-public-actions"><button className="teta-ghost-button" type="button" onClick={() => setView("login")}>ورود</button><button className="teta-primary-button compact" type="button" onClick={() => setView("register")}>شروع برای کلینیک</button></div>
      </header>

      <section className="teta-hero">
        <div className="teta-hero-copy">
          <span className="teta-hero-badge"><i /> AI dental intelligence for modern clinics</span>
          <h1>از یک تصویر OPG،<br /><em>تا تصمیم بالینی و ویزیت بعدی.</em></h1>
          <p>Teta2 — Teeth Evaluation & Treatment AI Assistant — به دندانپزشک کمک می‌کند مشکلات قابل مشاهده در OPG را مرور کند، برای هر دندان سابقه هوشمند بسازد و بیمار را در چرخه مراقبت نگه دارد.</p>
          <div className="teta-hero-actions"><button className="teta-primary-button hero-cta" type="button" onClick={() => setView("register")}>درخواست فعال‌سازی <span>↗</span></button><button className="teta-ghost-button hero-ghost" type="button" onClick={() => setView("login")}>ورود به داشبورد</button></div>
          <div className="teta-proof-row"><span><strong>9</strong> مدل تخصصی ONNX</span><span><strong>Private</strong> X-ray storage</span><span><strong>Human</strong> clinician review</span></div>
        </div>
        <div className="teta-hero-visual" aria-label="Teta2 product preview">
          <div className="teta-glow-orb" />
          <div className="teta-opg-card">
            <div className="teta-card-top"><span>OPG / AI Review</span><span className="teta-live-chip online">Ready</span></div>
            <div className="teta-opg-image"><div className="teta-jaw upper">◜ ◝ ◜ ◝ ◜ ◝ ◜ ◝</div><div className="teta-scan-line" /><div className="teta-jaw lower">◟ ◞ ◟ ◞ ◟ ◞ ◟ ◞</div><span className="teta-detection-box one">18</span><span className="teta-detection-box two">46</span></div>
            <div className="teta-findings-row"><article><span className="risk-dot amber" /><div><strong>Deep caries candidate</strong><small>Tooth 46 · review required</small></div><b>82%</b></article><article><span className="risk-dot violet" /><div><strong>Restoration detected</strong><small>Tooth 18 · historical context</small></div><b>94%</b></article></div>
          </div>
          <div className="teta-floating-card radar-mini"><span>⌁</span><div><small>Radar AI</small><strong>12 new opportunities</strong></div></div>
          <div className="teta-floating-card recall-mini"><span>↻</span><div><small>Smart Recall</small><strong>7 patients due</strong></div></div>
        </div>
      </section>

      <section className="teta-section" id="product"><div className="teta-section-heading"><span>یک پلتفرم، سه حلقه هوشمند</span><h2>تشخیص بهتر، پرونده زنده‌تر، رشد هوشمندتر کلینیک</h2></div><div className="teta-feature-grid">{features.map((feature) => <article key={feature.title}><span className="teta-feature-icon">{feature.icon}</span><small>{feature.kicker}</small><h3>{feature.title}</h3><p>{feature.copy}</p></article>)}</div></section>

      <section className="teta-radar-showcase" id="radar"><div><span className="teta-kicker">Radar AI</span><h2>بیمارانی را ببینید که همین حالا دنبال درمان هستند.</h2><p>Radar AI سیگنال‌های اجتماعی را به opportunity قابل بررسی تبدیل می‌کند؛ تیم کلینیک می‌تواند منبع، امتیاز، نیاز احتمالی و وضعیت پیگیری را در یک صفحه ببیند.</p><ul><li>رتبه‌بندی HOT / WARM / RESEARCH</li><li>فیلتر براساس پلتفرم، زبان، موقعیت و درمان</li><li>ثبت outcome برای بهبود workflow</li></ul></div><div className="teta-radar-panel"><div className="radar-pulse"><i /><i /><i /><span>T2</span></div><div className="radar-cards"><article><b>HOT · 91</b><strong>Implant consultation</strong><small>Instagram · Yerevan</small></article><article><b>WARM · 78</b><strong>Severe tooth pain</strong><small>Telegram · Armenia</small></article><article><b>HOT · 88</b><strong>Emergency dentist</strong><small>Facebook · Yerevan</small></article></div></div></section>

      <section className="teta-workflow" id="workflow"><div className="teta-section-heading"><span>Clinical loop</span><h2>Teta2 در جریان واقعی کلینیک</h2></div><div className="teta-steps"><article><b>01</b><h3>OPG را اضافه کنید</h3><p>تصویر در storage خصوصی کلینیک ذخیره می‌شود.</p></article><article><b>02</b><h3>AI تحلیل می‌کند</h3><p>مدل‌های V5 یافته‌ها را تولید و برای review آماده می‌کنند.</p></article><article><b>03</b><h3>دندانپزشک تأیید می‌کند</h3><p>نتیجه بدون clinician review به عنوان تشخیص نهایی ارائه نمی‌شود.</p></article><article><b>04</b><h3>پرونده ادامه پیدا می‌کند</h3><p>Follow-up و outreach بیمار را به مراقبت بعدی متصل می‌کنند.</p></article></div></section>

      <section className="teta-security" id="security"><div><span className="teta-kicker">Built for clinical data</span><h2>طراحی‌شده با جداسازی داده‌های کلینیک از ابتدا.</h2></div><div className="teta-security-grid"><span>Tenant-isolated PostgreSQL</span><span>Private S3 object storage</span><span>Short-lived authenticated access</span><span>Clinician-controlled AI findings</span></div></section>

      <section className="teta-final-cta"><span className="teta-tooth-mark large">T2</span><h2>نسل بعدی workflow دندانپزشکی را با Teta2 بسازید.</h2><p>AI برای جایگزین‌کردن پزشک نیست؛ برای اینکه پزشک سریع‌تر ببیند، بهتر پیگیری کند و فرصت‌های مهم را از دست ندهد ساخته شده است.</p><div><button className="teta-primary-button hero-cta" type="button" onClick={() => setView("register")}>شروع برای کلینیک</button><button className="teta-ghost-button hero-ghost" type="button" onClick={() => setView("login")}>ورود</button></div></section>
      <footer className="teta-public-footer"><div className="teta-logo-lockup"><span className="teta-tooth-mark">T2</span><strong>Teta2</strong></div><p>Teeth Evaluation & Treatment AI Assistant</p><small>AI-assisted clinical decision support · clinician review required</small></footer>
    </main>
  );
}
