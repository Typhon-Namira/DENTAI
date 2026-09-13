import { useEffect } from "react";
import { api, errorMessage } from "../api/client";

/**
 * ClinicalCareApp still owns the original Doctor-only React disabled prop.
 * For non-Doctor clinic roles we bridge that legacy UI guard to the now
 * role-neutral backend endpoint without duplicating the analysis UI itself.
 * Doctors continue through the original React handler unchanged.
 */
export function AllRolesAiRunAccess() {
  useEffect(() => {
    let nativeBusy = false;

    const controls = () => document.querySelector<HTMLElement>(".ai-control");
    const actionButton = () => controls()?.querySelector<HTMLButtonElement>("button.ai-action") ?? null;
    const xraySelect = () => controls()?.querySelectorAll<HTMLSelectElement>("select")?.[1] ?? null;
    const currentRole = () => document.querySelector<HTMLElement>(".care-doctor small")?.textContent?.trim().toUpperCase() ?? "";

    const clearFeedback = () => document.getElementById("all-roles-ai-feedback")?.remove();
    const showFeedback = (message: string, error = false) => {
      clearFeedback();
      const host = controls();
      if (!host) return;
      const feedback = document.createElement("div");
      feedback.id = "all-roles-ai-feedback";
      feedback.className = error ? "care-inline-error" : "flow-success";
      feedback.textContent = message;
      host.insertAdjacentElement("afterend", feedback);
    };

    const sync = () => {
      const button = actionButton();
      const xray = xraySelect();
      if (!button || !xray) return;
      if (currentRole() === "DOCTOR") return;
      const shouldDisable = !xray.value || nativeBusy;
      if (button.disabled !== shouldDisable) button.disabled = shouldDisable;
    };

    const handleClick = async (event: MouseEvent) => {
      const target = event.target instanceof Element ? event.target.closest<HTMLButtonElement>("button.ai-action") : null;
      if (!target || currentRole() === "DOCTOR") return;

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const xray = xraySelect();
      if (!xray?.value || nativeBusy) return;

      nativeBusy = true;
      clearFeedback();
      target.disabled = true;
      const originalHtml = target.innerHTML;
      target.textContent = "AI running…";

      try {
        await api.createAnalysis(xray.value);
        showFeedback("AI analysis started successfully.");
        window.location.reload();
      } catch (reason) {
        nativeBusy = false;
        target.innerHTML = originalHtml;
        showFeedback(errorMessage(reason), true);
        sync();
      }
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
    document.addEventListener("click", handleClick, true);

    return () => {
      observer.disconnect();
      document.removeEventListener("change", sync, true);
      document.removeEventListener("click", handleClick, true);
      clearFeedback();
    };
  }, []);

  return null;
}
