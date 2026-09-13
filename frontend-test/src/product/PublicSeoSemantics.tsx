import { useEffect } from "react";

const INDEXABLE = new Set(["/", "/product", "/how-it-works", "/pricing", "/clinical-safety", "/about"]);

function basePath(pathname: string): string | null {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  const match = normalized.match(/^\/(hy|ru)(?:\/(.*))?$/);
  if (match) {
    const rest = match[2]?.replace(/\/+$/, "") ?? "";
    const path = rest ? `/${rest}` : "/";
    return INDEXABLE.has(path) ? path : null;
  }
  return INDEXABLE.has(normalized) ? normalized : null;
}

function ensureSinglePageH1() {
  const path = basePath(window.location.pathname);
  if (!path || path === "/") return;

  const marketing = document.querySelector<HTMLElement>(".product-marketing-page");
  if (!marketing) return;

  const existing = marketing.querySelector("h1");
  if (existing) return;

  const firstDeckHeading = marketing.querySelector<HTMLHeadingElement>(".deck2-heading h2");
  const firstFallbackHeading = marketing.querySelector<HTMLHeadingElement>(".product-section-heading h2");
  const source = firstDeckHeading ?? firstFallbackHeading;
  if (!source) return;

  const replacement = document.createElement("h1");
  for (const attribute of Array.from(source.attributes)) {
    replacement.setAttribute(attribute.name, attribute.value);
  }
  replacement.innerHTML = source.innerHTML;
  source.replaceWith(replacement);
}

export function PublicSeoSemantics() {
  useEffect(() => {
    let scheduled = 0;
    const apply = () => {
      window.clearTimeout(scheduled);
      scheduled = window.setTimeout(ensureSinglePageH1, 0);
    };

    apply();
    const observer = new MutationObserver(apply);
    observer.observe(document.getElementById("root") ?? document.body, { childList: true, subtree: true });
    window.addEventListener("popstate", apply);
    window.addEventListener("teta2-localized-route", apply);
    window.addEventListener("teta2-language-change", apply);

    return () => {
      observer.disconnect();
      window.clearTimeout(scheduled);
      window.removeEventListener("popstate", apply);
      window.removeEventListener("teta2-localized-route", apply);
      window.removeEventListener("teta2-language-change", apply);
    };
  }, []);

  return null;
}
