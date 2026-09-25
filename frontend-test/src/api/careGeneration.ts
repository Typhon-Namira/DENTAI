import { authenticatedRequest } from "./client";
import type { CarePlan } from "./product";

export const careGenerationApi = {
  readiness(analysisId: string) {
    return authenticatedRequest<GenerationReadiness>(
      `/api/v1/care/analyses/${encodeURIComponent(analysisId)}/generation-readiness`
    );
  },
  generate(analysisId: string) {
    return authenticatedRequest<CarePlan>(
      `/api/v1/care/analyses/${encodeURIComponent(analysisId)}/generate-plan`,
      { method: "POST" }
    );
  }
};
