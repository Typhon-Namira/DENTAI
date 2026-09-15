import { describe, expect, it } from "vitest";

import { bookingStatusLabel, bookingText } from "./BookingExperience";

describe("booking appointment manager localization", () => {
  it("renders Armenian admin copy without English fallbacks", () => {
    expect(bookingText.hy.doctorApprovalAdmin).toBe("ԲԺՇԿԻ ՀԱՍՏԱՏՈՒՄ");
    expect(bookingText.hy.refresh).toBe("Թարմացնել");
    expect(bookingText.hy.calendar).toBe("ՕՐԱՑՈՒՅՑ");
    expect(bookingText.hy.noPending).toBe("Հաստատման սպասող այցի հարցումներ չկան։");
    expect(bookingText.hy.noUpcoming).toBe("Առաջիկա հաստատված այցեր դեռ չկան։");
  });

  it("renders Russian admin copy without English fallbacks", () => {
    expect(bookingText.ru.doctorApprovalAdmin).toBe("ПОДТВЕРЖДЕНИЕ ВРАЧА");
    expect(bookingText.ru.refresh).toBe("Обновить");
    expect(bookingText.ru.calendar).toBe("КАЛЕНДАРЬ");
    expect(bookingText.ru.noPending).toBe("Нет запросов на прием, ожидающих подтверждения.");
    expect(bookingText.ru.noUpcoming).toBe("Предстоящих подтвержденных приемов пока нет.");
  });

  it("localizes appointment statuses", () => {
    expect(bookingStatusLabel("CONFIRMED", "hy")).toBe("Հաստատված");
    expect(bookingStatusLabel("CONFIRMED", "ru")).toBe("Подтверждено");
    expect(bookingStatusLabel("RESCHEDULE_REQUESTED", "ru")).toBe("Запрошен перенос");
  });
});
