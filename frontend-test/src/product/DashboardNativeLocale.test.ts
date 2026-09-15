import { describe, expect, it } from "vitest";

import { translateDashboardText } from "./DashboardNativeLocale";

describe("native dashboard localization", () => {
  it("removes hybrid English from Armenian dashboard labels", () => {
    expect(translateDashboardText("Teta2 · կլինիկական follow-up workspace", "hy")).toBe(
      "Teta2 · կլինիկական հետագա հսկողության աշխատանքային միջավայր",
    );
    expect(translateDashboardText("Ակտիվ care պլաններ", "hy")).toBe("Ակտիվ խնամքի պլաններ");
    expect(translateDashboardText("Care API-ն դեռ տեղադրված չէ միացված backend-ում։", "hy")).toBe(
      "Հետագա հսկողության ծառայությունը դեռ հասանելի չէ միացված սերվերում։",
    );
  });

  it("renders legacy English dashboard surfaces as native Russian", () => {
    expect(translateDashboardText("AUTONOMOUS CARE LOOP", "ru")).toBe(
      "АВТОМАТИЗИРОВАННЫЙ ЦИКЛ НАБЛЮДЕНИЯ",
    );
    expect(translateDashboardText("Clinic schedule & AI booking memory", "ru")).toBe(
      "Расписание клиники и память ИИ для записи",
    );
    expect(translateDashboardText("Create the patient. Upload the OPG. Teta2 takes it from there.", "ru")).toBe(
      "Создайте карту пациента и загрузите ОПТГ. Дальнейший процесс организует Teta2.",
    );
  });

  it("localizes subscription states and live counters", () => {
    expect(translateDashboardText("Free · 12:04:09", "hy")).toBe("Անվճար · 12:04:09");
    expect(translateDashboardText("Premium · 18 days left", "ru")).toBe("Премиум · осталось 18 дн.");
    expect(translateDashboardText("PAYMENT REVIEW", "ru")).toBe("ПРОВЕРКА ОПЛАТЫ");
  });

  it("corrects Armenian status leakage when Russian is selected", () => {
    expect(translateDashboardText("Հերթագրված", "ru")).toBe("В очереди");
    expect(translateDashboardText("Խորը կարիես", "ru")).toBe("Глубокий кариес");
  });

  it("keeps English unchanged", () => {
    expect(translateDashboardText("Follow-up plans", "en")).toBe("Follow-up plans");
  });
});
