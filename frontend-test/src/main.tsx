import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { AllRolesAiRunAccess } from "./product/AllRolesAiRunAccess";
import { BookingExperience } from "./product/BookingExperience";
import { CareExperienceEnhancer } from "./product/CareExperienceEnhancer";
import { CareGenerationContractPanel } from "./product/CareGenerationContractPanel";
import { FollowupCaseWorkspace } from "./product/FollowupCaseWorkspace";
import { FrontendLocaleQuality } from "./product/FrontendLocaleQuality";
import { HomepageEvidenceSections } from "./product/HomepageEvidenceSections";
import { HomepageHeroFollowupAsset } from "./product/HomepageHeroFollowupAsset";
import { LegalLocaleQuality } from "./product/LegalLocaleQuality";
import { LocalizedPublicRouteBridge, prepareLocalizedPublicRoute } from "./product/publicLocaleRouting";
import { PageDeckSectionsV2 } from "./product/PageDeckSectionsV2";
import { PlatformAccessExperienceV2 } from "./product/PlatformAccessExperienceV2";
import ProductApp from "./product/ProductApp";
import { PublicSeo } from "./product/PublicSeo";
import "./styles/medical-workspace.css";
import "./v4/v4.css";
import "./v4/v4-real-opg.css";
import "./v4/v4-clinical-tools.css";
import "./v4/v4-opg-findings.css";
import "./v4/v4-opg-coordinate-fix.css";
import "./product/product.css";
import "./product/care-experience.css";
import "./product/followup-case.css";
import "./product/platform-access.css";
import "./product/public-chrome.css";
import "./product/brand-logo.css";
import "./product/home-hero-overrides.css";
import "./product/home-hero-composition.css";
import "./product/home-hero-fit.css";
import "./product/home-hero-fit-v2.css";
import "./product/home-hero-fit-v3.css";
import "./product/home-hero-workflow.css";
import "./product/home-hero-workflow-fix.css";
import "./product/home-hero-polish.css";
import "./product/home-hero-quality-title.css";
import "./product/home-hero-followup-hq.css";
import "./product/login-polish.css";
import "./product/booking-public-polish.css";
import "./product/page-deck-v2-polish.css";

prepareLocalizedPublicRoute();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <>
      <LocalizedPublicRouteBridge />
      <ProductApp />
      <BookingExperience />
      <PublicSeo />
      <HomepageHeroFollowupAsset />
      <HomepageEvidenceSections />
      <PageDeckSectionsV2 />
      <CareExperienceEnhancer />
      <CareGenerationContractPanel />
      <FollowupCaseWorkspace />
      <PlatformAccessExperienceV2 />
      <AllRolesAiRunAccess />
      <FrontendLocaleQuality />
      <LegalLocaleQuality />
    </>
  </StrictMode>
);
