import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import ProductApp from "./product/ProductApp";
import { CareCommandCenter } from "./product/CareCommandCenter";
import "./styles/medical-workspace.css";
import "./v4/v4.css";
import "./v4/v4-real-opg.css";
import "./v4/v4-clinical-tools.css";
import "./v4/v4-opg-findings.css";
import "./v4/v4-opg-coordinate-fix.css";
import "./product/product.css";
import "./product/care-command.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ProductApp />
    <CareCommandCenter />
  </StrictMode>
);
