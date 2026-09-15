import { useEffect, useState } from "react";

import { FrontendLocaleQuality } from "./FrontendLocaleQuality";

/**
 * The legacy text-rewrite layer is retained only for older public marketing pages.
 * Authenticated clinic UI is source-localized and must never be rewritten after render.
 */
export function PublicLocaleQualityGate() {
  const [clinicMounted, setClinicMounted] = useState(() => Boolean(document.querySelector(".care-shell")));

  useEffect(() => {
    const sync = () => setClinicMounted(Boolean(document.querySelector(".care-shell")));
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  return clinicMounted ? null : <FrontendLocaleQuality />;
}
