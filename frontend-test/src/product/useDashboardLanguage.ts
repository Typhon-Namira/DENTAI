import { useEffect, useState } from "react";

import { dashboardLang, type DashboardLang } from "./dashboardI18n";

export function useDashboardLanguage(): DashboardLang {
  const [lang, setLang] = useState<DashboardLang>(() => dashboardLang());

  useEffect(() => {
    const sync = () => setLang(dashboardLang());
    window.addEventListener("teta2-language-change", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("teta2-language-change", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  return lang;
}
