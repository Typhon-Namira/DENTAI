import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

import { CareExperienceEnhancer } from "./product/CareExperienceEnhancer";
import { CareGenerationContractPanel } from "./product/CareGenerationContractPanel";
import { FollowupCaseWorkspace } from "./product/FollowupCaseWorkspace";
import { AccessRequestPortal, CareOnlyMarketing, PlatformAdminPortal } from "./product/PlatformPortal";
import ProductApp from "./product/ProductApp";
import "./styles/medical-workspace.css";
import "./v4/v4.css";
import "./v4/v4-real-opg.css";
import "./v4/v4-clinical-tools.css";
import "./v4/v4-opg-findings.css";
import "./v4/v4-opg-coordinate-fix.css";
import "./product/product.css";
import "./product/care-experience.css";
import "./product/followup-case.css";
import "./product/platform-portal.css";

const ROUTE_EVENT = "teta2-route";

function installHistoryEvents() {
  const historyWithMarker = window.history as History & { __teta2EventsInstalled?: boolean };
  if (historyWithMarker.__teta2EventsInstalled) return;
  historyWithMarker.__teta2EventsInstalled = true;
  for (const method of ["pushState", "replaceState"] as const) {
    const original = window.history[method].bind(window.history);
    window.history[method] = ((...args: Parameters<History[typeof method]>) => {
      const result = original(...args);
      window.dispatchEvent(new Event(ROUTE_EVENT));
      return result;
    }) as History[typeof method];
  }
}

installHistoryEvents();

function RootRouter() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const sync = () => setPath(window.location.pathname);
    window.addEventListener("popstate", sync);
    window.addEventListener(ROUTE_EVENT, sync);
    return () => {
      window.removeEventListener("popstate", sync);
      window.removeEventListener(ROUTE_EVENT, sync);
    };
  }, []);

  if (path === "/register") return <AccessRequestPortal />;
  if (path === "/platform-admin") return <PlatformAdminPortal />;

  return <>
    <ProductApp />
    <CareExperienceEnhancer />
    <CareGenerationContractPanel />
    <FollowupCaseWorkspace />
    <CareOnlyMarketing />
  </>;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RootRouter />
  </StrictMode>
);
