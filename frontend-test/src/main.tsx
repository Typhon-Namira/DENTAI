import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { AllRolesAiRunAccess } from "./product/AllRolesAiRunAccess";
import { ArevikCofounder } from "./product/ArevikCofounder";
import { BookingExperience } from "./product/BookingExperience";
import { installCarePlanDateNormalizer } from "./product/carePlanDateNormalizer";
import { CareExperienceEnhancer } from "./product/CareExperienceEnhancer";
import { CareGenerationContractPanel } from "./product/CareGenerationContractPanel";
import { ClinicalWorkspaceRedesign } from "./product/ClinicalWorkspaceRedesign";
import { FreemiumCountryField } from "./product/FreemiumCountryField";
import { HomepageEvidenceSections } from "./product/HomepageEvidenceSections";
import { HomepageHeroFollowupAsset } from "./product/HomepageHeroFollowupAsset";
import { LegalLocaleQuality } from "./product/LegalLocaleQuality";
import { PageDeckSectionsV2 } from "./product/PageDeckSectionsV2";
import { PatientDriveExplorer } from "./product/PatientDriveExplorer";
import { PlatformAccessExperienceV2 } from "./product/PlatformAccessExperienceV2";
import { PlatformAdminControlCenter } from "./product/PlatformAdminControlCenter";
import ProductApp from "./product/ProductApp";
import { LocalizedPublicRouteBridge, prepareLocalizedPublicRoute } from "./product/publicLocaleRouting";
import { PublicLocaleQualityGate } from "./product/PublicLocaleQualityGate";
import { PublicSeo } from "./product/PublicSeo";
import { PublicSeoSemantics } from "./product/PublicSeoSemantics";
import { SeoAuthorityContent } from "./product/SeoAuthorityContent";
import { SettingsWorkspaceEnhancer } from "./product/SettingsWorkspaceEnhancer";
import { FreemiumPublicExperience, SubscriptionExperience } from "./product/SubscriptionExperience";
import "./styles/medical-workspace.css";
import "./v4/v4.css";
import "./v4/v4-real-opg.css";
import "./v4/v4-clinical-tools.css";
import "./v4/v4-opg-findings.css";
import "./v4/v4-opg-coordinate-fix.css";
import "./product/product.css";
import "./product/care-command.css";
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
installCarePlanDateNormalizer();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <>
      <LocalizedPublicRouteBridge />
      <ProductApp />
      <BookingExperience />
      <PublicSeo />
      <PublicSeoSemantics />
      <SeoAuthorityContent />
      <HomepageHeroFollowupAsset />
      <HomepageEvidenceSections />
      <PageDeckSectionsV2 />
      <ArevikCofounder />
      <CareExperienceEnhancer />
      <CareGenerationContractPanel />
      <ClinicalWorkspaceRedesign />
      <PatientDriveExplorer />
      <SettingsWorkspaceEnhancer />
      <PlatformAccessExperienceV2 />
      <PlatformAdminControlCenter />
      <FreemiumCountryField />
      <FreemiumPublicExperience />
      <SubscriptionExperience />
      <AllRolesAiRunAccess />
      <PublicLocaleQualityGate />
      <LegalLocaleQuality />
    </>
  </StrictMode>,
);