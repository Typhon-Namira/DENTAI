import { useEffect } from "react";

/**
 * The clinical analysis screen historically disabled Run AI analysis in the UI
 * for every role except DOCTOR. The API now authorizes every authenticated
 * clinic role, so keep the button state tied only to the real execution
 * prerequisites: an OPG must be selected and the action must not already be
 * running.
 */
export function AllRolesAiRunAccess() {
  useEffect(() => {
    const sync = () => {
      const controls = document.querySelector<HTMLElement>(".ai-control");
      const button = controls?.querySelector<HTMLButtonElement>("button.ai-action");
      const selects = controls?.querySelectorAll<HTMLSelectElement>("select");
      const xray = selects?.[1];
      if (!button || !xray) return;

      const running = /running|…/i.test(button.textContent ?? "");
      const shouldDisable = !xray.value || running;
      if (button.disabled !== shouldDisable) button.disabled = shouldDisable;
    };

    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["disabled", "value", "class"],
      characterData: true,
    });
    document.addEventListener("change", sync, true);
    return () => {
      observer.disconnect();
      document.removeEventListener("change", sync, true);
    };
  }, []);

  return null;
}
