import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import AppV4 from "./v4/AppV4";
import "./v4/v4.css";
import "./v4/v4-real-opg.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppV4 />
  </StrictMode>
);
