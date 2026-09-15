import { useEffect } from "react";

const INPUT_ID = "teta2-free-country-input";

export function FreemiumCountryField() {
  useEffect(() => {
    const sync = () => {
      if (!["/register", "/request-access"].includes(window.location.pathname)) return;
      const select = document.querySelector('select[name="country"]') as HTMLSelectElement | null;
      const existing = document.getElementById(INPUT_ID) as HTMLInputElement | null;
      if (!select) return;

      // The legacy paid-access form only offered Armenia/Russia because it was
      // coupled to market pricing. Free onboarding is global, so keep that
      // legacy control out of FormData and collect the clinic's real country.
      select.name = "legacy_market_country";
      select.required = false;
      select.style.display = "none";

      if (!existing) {
        const input = document.createElement("input");
        input.id = INPUT_ID;
        input.name = "country";
        input.required = true;
        input.autocomplete = "country-name";
        input.placeholder = "Country";
        select.insertAdjacentElement("afterend", input);
      }
    };

    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["name"],
    });
    window.addEventListener("popstate", sync);
    return () => {
      observer.disconnect();
      window.removeEventListener("popstate", sync);
    };
  }, []);

  return null;
}
