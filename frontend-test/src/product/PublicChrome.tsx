import { Activity, Check, ChevronDown, Menu, ShieldCheck, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export type PublicLanguage = "en" | "hy" | "ru";
export type PublicPath = "/" | "/product" | "/how-it-works" | "/pricing" | "/clinical-safety" | "/about" | "/login" | "/register" | "/privacy" | "/terms" | "/cookies" | "/payments" | "/clinical-disclaimer";

const LANGUAGE_NAMES: Record<PublicLanguage, string> = {
  en: "English",
  hy: "Հայերեն",
  ru: "Русский",
};

export function FlagIcon({ language }: { language: PublicLanguage }) {
  if (language === "hy") {
    return <svg className="t2-flag" viewBox="0 0 30 20" aria-hidden="true"><path fill="#d90012" d="M0 0h30v6.67H0z"/><path fill="#0033a0" d="M0 6.67h30v6.66H0z"/><path fill="#f2a800" d="M0 13.33h30V20H0z"/></svg>;
  }
  if (language === "ru") {
    return <svg className="t2-flag" viewBox="0 0 30 20" aria-hidden="true"><path fill="#fff" d="M0 0h30v6.67H0z"/><path fill="#0039a6" d="M0 6.67h30v6.66H0z"/><path fill="#d52b1e" d="M0 13.33h30V20H0z"/></svg>;
  }
  return <svg className="t2-flag" viewBox="0 0 30 20" aria-hidden="true"><path fill="#012169" d="M0 0h30v20H0z"/><path stroke="#fff" strokeWidth="4" d="m0 0 30 20M30 0 0 20"/><path stroke="#c8102e" strokeWidth="2" d="m0 0 30 20M30 0 0 20"/><path stroke="#fff" strokeWidth="7" d="M15 0v20M0 10h30"/><path stroke="#c8102e" strokeWidth="4" d="M15 0v20M0 10h30"/></svg>;
}

export function LanguageDropdown({ language, onChange }: { language: PublicLanguage; onChange: (language: PublicLanguage) => void }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const close = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);
  return <div className="t2-language" ref={root}>
    <button className="t2-language-trigger" aria-label={`Language: ${LANGUAGE_NAMES[language]}`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((value) => !value)}><FlagIcon language={language}/><ChevronDown/></button>
    {open && <div className="t2-language-menu" role="menu">{(["en","hy","ru"] as const).map((item) => <button key={item} role="menuitemradio" aria-checked={language === item} onClick={() => { onChange(item); setOpen(false); }}><FlagIcon language={item}/><span>{LANGUAGE_NAMES[item]}</span>{language === item && <Check/>}</button>)}</div>}
  </div>;
}

export type ChromeCopy = {
  product: string; how: string; pricing: string; safety: string; about: string; login: string; access: string;
};

const LINKS: Array<[PublicPath, keyof Pick<ChromeCopy,"product"|"how"|"pricing"|"safety"|"about">]> = [
  ["/product","product"], ["/how-it-works","how"], ["/pricing","pricing"], ["/clinical-safety","safety"], ["/about","about"],
];

export function PublicNavbar({ language, onLanguage, copy, route, go }: { language: PublicLanguage; onLanguage: (language: PublicLanguage) => void; copy: ChromeCopy; route: string; go: (path: PublicPath) => void }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = (path: PublicPath) => { setMobileOpen(false); go(path); };
  return <header className="t2-navbar">
    <button className="t2-wordmark" onClick={() => navigate("/")} aria-label="Teta2 home"><span>Teta2</span><small><Activity/>Clinical AI</small></button>
    <button className="t2-menu-trigger" aria-label="Open navigation" aria-expanded={mobileOpen} onClick={() => setMobileOpen((value) => !value)}>{mobileOpen ? <X/> : <Menu/>}</button>
    <nav className={mobileOpen ? "open" : ""} aria-label="Primary navigation">{LINKS.map(([path,key]) => <button key={path} className={route === path ? "active" : ""} onClick={() => navigate(path)}>{copy[key]}</button>)}<button className="t2-mobile-only" onClick={() => navigate("/login")}>{copy.login}</button><button className="t2-mobile-only" onClick={() => navigate("/register")}>{copy.access}</button></nav>
    <div className="t2-nav-actions"><button className="t2-login-link" onClick={() => navigate("/login")}>{copy.login}</button><button className="t2-access-button" onClick={() => navigate("/register")}>{copy.access}</button><LanguageDropdown language={language} onChange={onLanguage}/></div>
  </header>;
}

const FOOTER_COPY = {
  en: { platform: "Platform", legal: "Legal & trust", contact: "Contact", privacy: "Privacy policy", terms: "Terms of service", cookies: "Cookies & browser storage", payments: "Payments & refunds", clinical: "Clinical AI disclaimer", status: "Pre-incorporation software project", jurisdiction: "Governed by the laws of Armenia" },
  hy: { platform: "Հարթակ", legal: "Իրավական և վստահություն", contact: "Կապ", privacy: "Գաղտնիության քաղաքականություն", terms: "Ծառայության պայմաններ", cookies: "Cookie-ներ և browser storage", payments: "Վճարումներ և վերադարձներ", clinical: "Կլինիկական AI-ի սահմանափակումներ", status: "Մինչև ընկերության գրանցումը գործող ծրագրային նախագիծ", jurisdiction: "Կարգավորվում է Հայաստանի Հանրապետության օրենքներով" },
  ru: { platform: "Платформа", legal: "Правовая информация", contact: "Контакты", privacy: "Политика конфиденциальности", terms: "Условия использования", cookies: "Cookie и хранилище браузера", payments: "Оплата и возвраты", clinical: "Отказ от медицинских гарантий ИИ", status: "Программный проект до регистрации компании", jurisdiction: "Регулируется законодательством Армении" },
} as const;

export function PublicFooter({ copy, description, language, go }: { copy: ChromeCopy; description: string; language: PublicLanguage; go: (path: PublicPath) => void }) {
  const f = FOOTER_COPY[language];
  return <footer className="t2-footer"><div className="t2-footer-main"><section className="t2-footer-brand"><button className="t2-wordmark" onClick={() => go("/")}><span>Teta2</span></button><p>{description}</p><span className="t2-footer-status"><ShieldCheck/>{f.status}</span></section><nav aria-label={f.platform}><strong>{f.platform}</strong>{LINKS.map(([path,key]) => <button key={path} onClick={() => go(path)}>{copy[key]}</button>)}<button onClick={() => go("/login")}>{copy.login}</button><button onClick={() => go("/register")}>{copy.access}</button></nav><nav aria-label={f.legal}><strong>{f.legal}</strong><button onClick={() => go("/privacy")}>{f.privacy}</button><button onClick={() => go("/terms")}>{f.terms}</button><button onClick={() => go("/cookies")}>{f.cookies}</button><button onClick={() => go("/payments")}>{f.payments}</button><button onClick={() => go("/clinical-disclaimer")}>{f.clinical}</button></nav><section className="t2-footer-contact"><strong>{f.contact}</strong><a href="mailto:teta2support@gmail.com">teta2support@gmail.com</a><p>{f.jurisdiction}</p></section></div><div className="t2-footer-bottom"><small>© {new Date().getFullYear()} Teta2</small><small>{f.status}</small></div></footer>;
}

export function StorageNotice({ language, onPolicy }: { language: PublicLanguage; onPolicy: () => void }) {
  const key = "teta2-storage-notice-v1";
  const [visible, setVisible] = useState(() => localStorage.getItem(key) !== "seen");
  if (!visible) return null;
  const copy = language === "hy" ? { title: "Միայն անհրաժեշտ browser storage", body: "Teta2-ը չի օգտագործում գովազդային կամ analytics cookie-ներ։ Լեզուն պահվում է այս սարքում, իսկ մուտքի տվյալները՝ միայն browser session-ի ընթացքում։", accept: "Հասկացա", policy: "Մանրամասներ" } : language === "ru" ? { title: "Только необходимое хранилище браузера", body: "Teta2 не использует рекламные или аналитические cookie. Язык сохраняется на этом устройстве, а данные входа — только на время сессии браузера.", accept: "Понятно", policy: "Подробнее" } : { title: "Essential browser storage only", body: "Teta2 does not use advertising or analytics cookies. Your language is saved on this device; sign-in tokens stay only for the browser session.", accept: "Understood", policy: "Read policy" };
  return <aside className="t2-storage-notice" aria-label={copy.title}><ShieldCheck/><div><strong>{copy.title}</strong><p>{copy.body}</p></div><div><button className="secondary" onClick={onPolicy}>{copy.policy}</button><button onClick={() => { localStorage.setItem(key, "seen"); setVisible(false); }}>{copy.accept}</button></div></aside>;
}

export function FirstVisitLanguageModal({ onSelect }: { onSelect: (language: PublicLanguage) => void }) {
  return <div className="t2-language-modal-backdrop" role="presentation"><section className="t2-language-modal" role="dialog" aria-modal="true" aria-label="Choose language"><div className="t2-modal-signal" aria-hidden="true"><Sparkles /></div><div className="t2-modal-flags">{(["en","hy","ru"] as const).map((language) => <button key={language} onClick={() => onSelect(language)} aria-label={LANGUAGE_NAMES[language]} title={LANGUAGE_NAMES[language]}><FlagIcon language={language}/></button>)}</div></section></div>;
}
