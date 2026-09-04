import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import AppV4 from "./v4/AppV4";
import "./styles/medical-workspace.css";
import "./v4/v4.css";
import "./v4/v4-real-opg.css";
import "./v4/v4-clinical-tools.css";
import "./v4/v4-opg-findings.css";
import "./v4/v4-opg-coordinate-fix.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppV4 />
  </StrictMode>
);
