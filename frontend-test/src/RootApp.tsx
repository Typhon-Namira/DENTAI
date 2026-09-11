import { useCallback, useEffect, useState } from "react";

import { AdminPanel } from "./components/AdminPanel";
import type { Lang } from "./i18n";
import { PlatformAccessRequestPage } from "./product/PlatformAccessRequestPage";
import { PlatformPricingPage } from "./product/PlatformPricingPage";
import ProductApp from "./product/ProductApp";

const ROUTE_EVENT = "teta2-route-change";

function currentPath(): string {
  return window.location.pathname || "/";
}

function storedLang(): Lang {
  const value = localStorage.getItem("teta2-product-language") ?? localStorage.getItem("teta2-v4-language");
  return value === "hy" ? "hy" : "en";
}

export function RootApp() {
  const [path, setPath] = useState(currentPath);
  const [lang, setLangState] = useState<Lang>(storedLang);

  useEffect(() => {
    const originalPushState = window.history.pushState.bind(window.history);
    const originalReplaceState = window.history.replaceState.bind(window.history);
    const notify = () => window.dispatchEvent(new Event(ROUTE_EVENT));
    window.history.pushState = ((...args: Parameters<History["pushState"]>) => {
      originalPushState(...args);
      notify();
    }) as History["pushState"];
    window.history.replaceState = ((...args: Parameters<History["replaceState"]>) => {
      originalReplaceState(...args);
      notify();
    }) as History["replaceState"];
    const sync = () => setPath(currentPath());
    window.addEventListener("popstate", sync);
    window.addEventListener(ROUTE_EVENT, sync);
    return () => {
      window.history.pushState = originalPushState;
      window.history.replaceState = originalReplaceState;
      window.removeEventListener("popstate", sync);
      window.removeEventListener(ROUTE_EVENT, sync);
    };
  }, []);

  const go = useCallback((next: string) => {
    window.history.pushState({}, "", next);
    setPath(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const setLang = useCallback((next: Lang) => {
    localStorage.setItem("teta2-product-language", next);
    localStorage.setItem("teta2-v4-language", next);
    document.documentElement.lang = next;
    setLangState(next);
  }, []);

  if (path === "/admin") {
    return <AdminPanel lang={lang} setLang={setLang} onExit={() => go("/")} />;
  }
  if (path === "/register" || path === "/request-access") {
    return <PlatformAccessRequestPage lang={lang} go={go} />;
  }
  if (path === "/pricing") {
    return <PlatformPricingPage lang={lang} go={go} />;
  }
  return <ProductApp />;
}
