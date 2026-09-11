import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { RootApp } from "./RootApp";
import { CareExperienceEnhancer } from "./product/CareExperienceEnhancer";
import { CareGenerationContractPanel } from "./product/CareGenerationContractPanel";
import { FollowupCaseWorkspace } from "./product/FollowupCaseWorkspace";
import "./styles/medical-workspace.css";
import "./styles/teta2-platform.css";
import "./v4/v4.css";
import "./v4/v4-real-opg.css";
import "./v4/v4-clinical-tools.css";
import "./v4/v4-opg-findings.css";
import "./v4/v4-opg-coordinate-fix.css";
import "./product/product.css";
import "./product/care-experience.css";
import "./product/followup-case.css";
import "./product/platform-access.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <>
      <RootApp />
      <CareExperienceEnhancer />
      <CareGenerationContractPanel />
      <FollowupCaseWorkspace />
    </>
  </StrictMode>,
);
