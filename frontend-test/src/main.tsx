import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Teta2App from "./Teta2App";
import "./styles/index.css";
import "./styles/workspace-redesign.css";
import "./styles/medical-workspace.css";
import "./styles/patient-radar.css";
import "./styles/teta2-platform.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Teta2App />
  </StrictMode>
);
