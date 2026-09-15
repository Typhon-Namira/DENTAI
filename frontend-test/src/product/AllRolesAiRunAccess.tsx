import { useEffect } from "react";

type ReactButtonProps = {
  disabled?: boolean;
  onClick?: (event: MouseEvent) => unknown;
};

function reactButtonProps(button: HTMLButtonElement): ReactButtonProps | null {
  const key = Object.keys(button).find((item) => item.startsWith("__reactProps$"));
  if (!key) return null;
  return (button as unknown as Record<string, ReactButtonProps>)[key] ?? null;
}

/**
 * Compatibility bridge for the legacy role-gated AI action.
 * It deliberately avoids reading localized role labels so language changes can
 * never alter permissions or button availability.
 */
export function AllRolesAiRunAccess() {
  useEffect(() => {
    const controls = () => document.querySelector<HTMLElement>(".ai-control");
    const actionButton = () => controls()?.querySelector<HTMLButtonElement>("button.ai-action") ?? null;
    const xraySelect = () => controls()?.querySelectorAll<HTMLSelectElement>("select")?.[1] ?? null;

    const sync = () => {
      const button = actionButton();
      const xray = xraySelect();
      if (!button || !xray) return;

      const running = /running|ընթացքի մեջ|выполняется|…/i.test(button.textContent ?? "");
      const shouldDisable = !xray.value || running;
      if (button.disabled !== shouldDisable) button.disabled = shouldDisable;

      const props = reactButtonProps(button);
      if (props && props.disabled !== shouldDisable) props.disabled = shouldDisable;
    };

    const handleClick = (event: MouseEvent) => {
      const target = event.target instanceof Element
        ? event.target.closest<HTMLButtonElement>("button.ai-action")
        : null;
      if (!target) return;
      const xray = xraySelect();
      if (!xray?.value) return;
      const props = reactButtonProps(target);
      if (!props?.onClick) return;

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      if (target.disabled) target.disabled = false;
      if (props.disabled) props.disabled = false;
      props.onClick(event);
    };

    sync();
    const timer = window.setInterval(sync, 300);
    document.addEventListener("change", sync, true);
    document.addEventListener("focusin", sync, true);
    document.addEventListener("click", handleClick, true);

    return () => {
      window.clearInterval(timer);
      document.removeEventListener("change", sync, true);
      document.removeEventListener("focusin", sync, true);
      document.removeEventListener("click", handleClick, true);
    };
  }, []);

  return null;
}
