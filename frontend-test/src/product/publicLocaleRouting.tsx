import { useLayoutEffect } from "react";

export type SeoPublicLanguage = "en" | "hy" | "ru";
export type SeoPublicPath = "/" | "/product" | "/how-it-works" | "/pricing" | "/clinical-safety" | "/about";

export const SEO_PUBLIC_PATHS: readonly SeoPublicPath[] = [
  "/",
  "/product",
  "/how-it-works",
  "/pricing",
  "/clinical-safety",
  "/about",
];

const SEO_PATH_SET = new Set<string>(SEO_PUBLIC_PATHS);
const LANG_KEY = "teta2-product-language";
const LEGACY_LANG_KEY = "teta2-v4-language";

let bootRestorePath: string | null = null;
let activeLanguage: SeoPublicLanguage = "en";

function normalizePath(pathname: string): string {
  if (!pathname || pathname === "/") return "/";
  const normalized = pathname.startsWith("/") ? pathname : `/${pathname}`;
  return normalized.replace(/\/+$/, "") || "/";
}

function storedLanguage(): SeoPublicLanguage | null {
  const value = localStorage.getItem(LANG_KEY) ?? localStorage.getItem(LEGACY_LANG_KEY);
  return value === "en" || value === "hy" || value === "ru" ? value : null;
}

function persistLanguage(language: SeoPublicLanguage): void {
  localStorage.setItem(LANG_KEY, language);
  localStorage.setItem(LEGACY_LANG_KEY, language);
  document.documentElement.lang = language;
}

export function parseLocalizedPublicPath(pathname: string): {
  basePath: SeoPublicPath;
  language: SeoPublicLanguage;
  localized: boolean;
} | null {
  const normalized = normalizePath(pathname);
  const localizedMatch = normalized.match(/^\/(hy|ru)(?:\/(.*))?$/);
  if (localizedMatch) {
    const language = localizedMatch[1] as Exclude<SeoPublicLanguage, "en">;
    const rest = localizedMatch[2]?.replace(/\/+$/, "") ?? "";
    const basePath = (rest ? `/${rest}` : "/") as SeoPublicPath;
    if (!SEO_PATH_SET.has(basePath)) return null;
    return { basePath, language, localized: true };
  }

  if (!SEO_PATH_SET.has(normalized)) return null;
  return { basePath: normalized as SeoPublicPath, language: "en", localized: false };
}

export function localizedPublicPath(basePath: SeoPublicPath, language: SeoPublicLanguage): string {
  if (language === "en") return basePath;
  if (basePath === "/") return `/${language}/`;
  return `/${language}${basePath}`;
}

export function publicAlternateUrls(baseUrl: string, basePath: SeoPublicPath): Record<SeoPublicLanguage | "x-default", string> {
  const root = baseUrl.replace(/\/+$/, "");
  const absolute = (language: SeoPublicLanguage) => `${root}${localizedPublicPath(basePath, language)}`;
  return {
    en: absolute("en"),
    hy: absolute("hy"),
    ru: absolute("ru"),
    "x-default": absolute("en"),
  };
}

function dispatchLocalizedRoute(): void {
  window.dispatchEvent(new CustomEvent("teta2-localized-route"));
}

function restoreVisibleLocalizedPath(basePath: SeoPublicPath, language: SeoPublicLanguage): void {
  const target = `${localizedPublicPath(basePath, language)}${window.location.search}${window.location.hash}`;
  window.history.replaceState(window.history.state, "", target);
  dispatchLocalizedRoute();
}

/**
 * Runs before React renders. Localized SEO URLs are temporarily exposed to the
 * legacy SPA as their base route so every existing public component keeps the
 * exact same routing behaviour. A layout-effect bridge restores the visible
 * localized URL before passive SEO effects run.
 */
export function prepareLocalizedPublicRoute(): void {
  const parsed = parseLocalizedPublicPath(window.location.pathname);
  if (!parsed) return;

  activeLanguage = parsed.language;
  if (parsed.localized) {
    persistLanguage(parsed.language);
    bootRestorePath = localizedPublicPath(parsed.basePath, parsed.language);
    window.history.replaceState(
      window.history.state,
      "",
      `${parsed.basePath}${window.location.search}${window.location.hash}`,
    );
    return;
  }

  // An unprefixed SEO URL is the English URL. If a returning visitor had a
  // previous explicit language preference, keep URL and rendered language in
  // sync. For a true first visit we leave storage untouched so the existing
  // language-choice modal still behaves exactly as before.
  if (storedLanguage() !== null) persistLanguage("en");
  else document.documentElement.lang = "en";
}

export function LocalizedPublicRouteBridge() {
  useLayoutEffect(() => {
    const handlePopState = () => {
      const parsed = parseLocalizedPublicPath(window.location.pathname);
      if (!parsed) return;

      if (parsed.localized) {
        activeLanguage = parsed.language;
        persistLanguage(parsed.language);
        const basePath = parsed.basePath;
        window.history.replaceState(
          window.history.state,
          "",
          `${basePath}${window.location.search}${window.location.hash}`,
        );
        queueMicrotask(() => restoreVisibleLocalizedPath(basePath, parsed.language));
        return;
      }

      const preferred = storedLanguage() ?? activeLanguage;
      activeLanguage = preferred;
      if (preferred === "hy" || preferred === "ru") {
        const basePath = parsed.basePath;
        queueMicrotask(() => restoreVisibleLocalizedPath(basePath, preferred));
      } else {
        document.documentElement.lang = "en";
      }
    };

    const handleLanguageChange = (event: Event) => {
      const requested = (event as CustomEvent<SeoPublicLanguage>).detail;
      const next: SeoPublicLanguage = requested === "hy" || requested === "ru" ? requested : "en";
      activeLanguage = next;
      persistLanguage(next);

      const parsed = parseLocalizedPublicPath(window.location.pathname);
      if (!parsed) return;
      restoreVisibleLocalizedPath(parsed.basePath, next);
    };

    window.addEventListener("popstate", handlePopState);
    window.addEventListener("teta2-language-change", handleLanguageChange);

    if (bootRestorePath) {
      window.history.replaceState(
        window.history.state,
        "",
        `${bootRestorePath}${window.location.search}${window.location.hash}`,
      );
      bootRestorePath = null;
      dispatchLocalizedRoute();
    }

    return () => {
      window.removeEventListener("popstate", handlePopState);
      window.removeEventListener("teta2-language-change", handleLanguageChange);
    };
  }, []);

  return null;
}
