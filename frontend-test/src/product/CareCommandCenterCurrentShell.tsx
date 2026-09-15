import { useLayoutEffect } from "react";

import { CareCommandCenter as LegacyCareCommandCenter } from "./CareCommandCenter";

const SHELL_ALIASES = [
  [".care-sidebar", "clinic-sidebar"],
  [".care-main", "clinic-main"],
  [".care-shell", "clinic-shell"],
  [".care-quick-patient", "clinic-patient-select"]
] as const;

/**
 * Adapts the legacy Teta2 AI command center to the current clinical dashboard
 * without changing its backend/API behavior.
 *
 * On a hard refresh ProductApp first renders its session-restoring screen and
 * mounts ClinicalCareApp only after api.me() succeeds. Therefore the `.care-*`
 * shell may not exist when this component first mounts. Keep watching for the
 * live dashboard shell and apply the legacy aliases whenever those nodes appear
 * or are replaced.
 */
export function CareCommandCenter() {
  useLayoutEffect(() => {
    const ownedAliases = new Map<Element, Set<string>>();

    const applyAliases = () => {
      let addedAlias = false;

      for (const [selector, alias] of SHELL_ALIASES) {
        document.querySelectorAll(selector).forEach((node) => {
          if (node.classList.contains(alias)) return;

          node.classList.add(alias);
          addedAlias = true;

          const aliases = ownedAliases.get(node) ?? new Set<string>();
          aliases.add(alias);
          ownedAliases.set(node, aliases);
        });
      }

      // CareCommandCenter watches child-list changes. When aliases are applied
      // after the dashboard appears, emit one harmless child-list mutation so
      // its observer immediately re-resolves the newly aliased targets.
      if (addedAlias && document.body) {
        const marker = document.createComment("teta2-care-shell-ready");
        document.body.appendChild(marker);
        marker.remove();
      }
    };

    applyAliases();

    const observer = new MutationObserver(applyAliases);
    observer.observe(document.documentElement, { childList: true, subtree: true });

    return () => {
      observer.disconnect();
      ownedAliases.forEach((aliases, node) => {
        aliases.forEach((alias) => node.classList.remove(alias));
      });
    };
  }, []);

  return <LegacyCareCommandCenter />;
}
