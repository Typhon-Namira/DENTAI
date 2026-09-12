import { expect, test } from "@playwright/test";

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "laptop", width: 1366, height: 768 },
  { name: "desktop", width: 1920, height: 1080 },
];

for (const viewport of viewports) {
  test(`${viewport.name} clinical pages have no horizontal overflow`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto(process.env.CARE_E2E_URL ?? "http://127.0.0.1:5173/");

    // Production intentionally shows a first-visit language picker before the
    // rest of the public UI becomes interactive. The deploy verification must
    // complete that real first-visit step instead of trying to click through
    // the modal backdrop.
    const languageModal = page.getByRole("dialog", { name: "Choose language" });
    if (await languageModal.isVisible()) {
      await languageModal.getByRole("button", { name: "English", exact: true }).click();
      await expect(languageModal).toBeHidden();
    }

    await page.evaluate(() => {
      window.history.pushState({}, "", "/login");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await page.getByRole("textbox", { name: "Email or username" }).fill(process.env.CARE_E2E_USER ?? "doctor");
    await page.getByRole("textbox", { name: "Password" }).fill(process.env.CARE_E2E_PASSWORD ?? "VisualPass123!");
    await page.getByRole("textbox", { name: "Clinic slug" }).fill(process.env.CARE_E2E_CLINIC ?? "visual");
    await page.getByRole("button", { name: /sign in securely/i }).click();
    await expect(page.getByText("Your clinical day, in one place.")).toBeVisible();

    const clinicalNavigation = page.getByRole("navigation", { name: "Clinical workspace" });
    const labels = ["Dashboard", "Patients & records", "OPG + AI", "Follow-up plans", "Appointments", "Working hours"];

    for (const label of labels) {
      if (viewport.width <= 760) {
        if (!(await clinicalNavigation.isVisible())) {
          await page.getByRole("button", { name: "Open navigation" }).click();
          await expect(clinicalNavigation).toBeVisible();
        }
      }

      await clinicalNavigation.getByRole("button", { name: label }).click();

      const overflowReport = await page.evaluate(() => {
        const viewportWidth = document.documentElement.clientWidth;
        const offenders = [...document.querySelectorAll<HTMLElement>("body *")]
          .map((element) => {
            const bounds = element.getBoundingClientRect();
            return {
              element: `${element.tagName.toLowerCase()}${element.id ? `#${element.id}` : ""}${[...element.classList].slice(0, 3).map((name) => `.${name}`).join("")}`,
              left: Math.round(bounds.left),
              right: Math.round(bounds.right),
              width: Math.round(bounds.width),
            };
          })
          .filter(({ left, right }) => left < -1 || right > viewportWidth + 1)
          .sort((a, b) => b.right - viewportWidth - (a.right - viewportWidth))
          .slice(0, 8);
        return {
          overflow: document.documentElement.scrollWidth - viewportWidth,
          offenders,
        };
      });
      expect(
        overflowReport.overflow,
        `${label} overflows at ${viewport.width}px: ${JSON.stringify(overflowReport.offenders)}`,
      ).toBeLessThanOrEqual(1);
    }
  });
}
