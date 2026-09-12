import { Check, ChevronDown, Menu, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export type PublicLanguage = "en" | "hy" | "ru";
export type PublicPath = "/" | "/product" | "/how-it-works" | "/pricing" | "/clinical-safety" | "/about" | "/login" | "/register";

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
    <button className="t2-wordmark" onClick={() => navigate("/")} aria-label="Teta2 home">Teta2</button>
    <button className="t2-menu-trigger" aria-label="Open navigation" aria-expanded={mobileOpen} onClick={() => setMobileOpen((value) => !value)}>{mobileOpen ? <X/> : <Menu/>}</button>
    <nav className={mobileOpen ? "open" : ""} aria-label="Primary navigation">{LINKS.map(([path,key]) => <button key={path} className={route === path ? "active" : ""} onClick={() => navigate(path)}>{copy[key]}</button>)}<button className="t2-mobile-only" onClick={() => navigate("/login")}>{copy.login}</button><button className="t2-mobile-only" onClick={() => navigate("/register")}>{copy.access}</button></nav>
    <div className="t2-nav-actions"><button className="t2-login-link" onClick={() => navigate("/login")}>{copy.login}</button><button className="t2-access-button" onClick={() => navigate("/register")}>{copy.access}</button><LanguageDropdown language={language} onChange={onLanguage}/></div>
  </header>;
}

export function PublicFooter({ copy, description, go }: { copy: ChromeCopy; description: string; go: (path: PublicPath) => void }) {
  return <footer className="t2-footer"><div><button className="t2-wordmark" onClick={() => go("/")}>Teta2</button><p>{description}</p></div><nav aria-label="Footer navigation">{LINKS.map(([path,key]) => <button key={path} onClick={() => go(path)}>{copy[key]}</button>)}<button onClick={() => go("/login")}>{copy.login}</button><button onClick={() => go("/register")}>{copy.access}</button></nav><small>© {new Date().getFullYear()} Teta2</small></footer>;
}

export function FirstVisitLanguageModal({ onSelect }: { onSelect: (language: PublicLanguage) => void }) {
  return <div className="t2-language-modal-backdrop" role="presentation"><section className="t2-language-modal" role="dialog" aria-modal="true" aria-label="Choose language"><div className="t2-modal-signal" aria-hidden="true"><Sparkles /></div><div className="t2-modal-flags">{(["en","hy","ru"] as const).map((language) => <button key={language} onClick={() => onSelect(language)} aria-label={LANGUAGE_NAMES[language]} title={LANGUAGE_NAMES[language]}><FlagIcon language={language}/></button>)}</div></section></div>;
}
