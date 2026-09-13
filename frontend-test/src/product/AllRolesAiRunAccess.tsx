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

export function AllRolesAiRunAccess() {
  useEffect(() => {
    const controls = () => document.querySelector<HTMLElement>(".ai-control");
    const actionButton = () =>
      controls()?.querySelector<HTMLButtonElement>("button.ai-action") ?? null;
    const xraySelect = () =>
      controls()?.querySelectorAll<HTMLSelectElement>("select")?.[1] ?? null;
    const currentRole = () =>
      document
        .querySelector<HTMLElement>(".care-doctor small")
        ?.textContent?.trim()
        .toUpperCase() ?? "";

    const sync = () => {
      const button = actionButton();
      const xray = xraySelect();
      if (!button || !xray || currentRole() === "DOCTOR") return;
      const running = /AI running|…/i.test(button.textContent ?? "");
      const shouldDisable = !xray.value || running;
      button.disabled = shouldDisable;
      const props = reactButtonProps(button);
      if (props) props.disabled = shouldDisable;
    };

    const handleClick = (event: MouseEvent) => {
      const target =
        event.target instanceof Element
          ? event.target.closest<HTMLButtonElement>("button.ai-action")
          : null;
      if (!target || currentRole() === "DOCTOR") return;

      const xray = xraySelect();
      if (!xray?.value) return;

      const props = reactButtonProps(target);
      if (!props?.onClick) return;

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      target.disabled = false;
      props.disabled = false;
      props.onClick(event);
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
    };
  }, []);

  return null;
}
