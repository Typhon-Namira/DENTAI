import { useLayoutEffect } from "react";

import { CareCommandCenter as LegacyCareCommandCenter } from "./CareCommandCenter";
import "./care-command-current-shell.css";

const SELECTOR_ALIASES: Record<string, string> = {
  ".clinic-sidebar nav": ".care-sidebar nav",
  ".clinic-main": ".care-main",
  ".clinic-shell": ".care-shell",
  ".clinic-sidebar nav > button:not(.care-nav-button)": ".care-sidebar nav > button:not(.care-nav-button)",
  ".clinic-patient-select select": ".care-quick-patient select"
};

type SimpleDocumentQueries = {
  querySelector: (selectors: string) => Element | null;
  querySelectorAll: (selectors: string) => NodeListOf<Element>;
};

/**
 * Compatibility mount for the current clinical dashboard shell.
 *
 * CareCommandCenter predates the current `.care-*` shell class names and still
 * queries the former `.clinic-*` selectors. Keep the command-center behavior
 * untouched and translate only those exact legacy selectors while it is mounted.
 */
export function CareCommandCenter() {
  useLayoutEffect(() => {
    const doc = document as unknown as SimpleDocumentQueries;
    const originalQuerySelector = doc.querySelector;
    const originalQuerySelectorAll = doc.querySelectorAll;

    doc.querySelector = (selectors: string) =>
      originalQuerySelector.call(document, SELECTOR_ALIASES[selectors] ?? selectors);
    doc.querySelectorAll = (selectors: string) =>
      originalQuerySelectorAll.call(document, SELECTOR_ALIASES[selectors] ?? selectors);

    return () => {
      doc.querySelector = originalQuerySelector;
      doc.querySelectorAll = originalQuerySelectorAll;
    };
  }, []);

  return <LegacyCareCommandCenter />;
}
