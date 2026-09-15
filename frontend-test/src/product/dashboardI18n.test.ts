import { describe, expect, it } from "vitest";

import { dashboardFinding, dashboardStatus, dashboardText } from "./dashboardI18n";

describe("source-level dashboard i18n", () => {
  it("uses native Armenian source copy instead of hybrid English", () => {
    expect(dashboardText("hy", "subtitle")).toBe("Teta2 · կլինիկական հետագա հսկողության աշխատանքային միջավայր");
    expect(dashboardText("hy", "analysisLead")).not.toMatch(/\bfollow-up\b|\bfindings\b|\bworkspace\b|\bcare\b/i);
    expect(dashboardText("hy", "automaticPlan")).not.toMatch(/automatic|care-plan/i);
  });

  it("uses native Russian source copy for clinical dashboard surfaces", () => {
    expect(dashboardText("ru", "analysisTitle")).toBe("Анализ ОПТГ и решение врача");
    expect(dashboardText("ru", "breaksUnavailable")).toBe("Перерывы и недоступные периоды");
    expect(dashboardText("ru", "noConfirmedAppointments")).toBe("Подтвержденных приемов пока нет.");
  });

  it("localizes backend status and finding enums", () => {
    expect(dashboardStatus("PENDING_APPROVAL", "hy")).toBe("Սպասում է հաստատման");
    expect(dashboardStatus("PENDING_APPROVAL", "ru")).toBe("Ожидает подтверждения");
    expect(dashboardFinding("DEEP_CARIES", "hy")).toBe("Խորը կարիես");
    expect(dashboardFinding("DEEP_CARIES", "ru")).toBe("Глубокий кариес");
  });
});
