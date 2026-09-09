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
    await page.goto(process.env.CARE_E2E_URL ?? "http://127.0.0.1:5173/login");
    await page.locator('input[autocomplete="username"]').fill(process.env.CARE_E2E_USER ?? "doctor");
    await page.locator('input[autocomplete="current-password"]').fill(process.env.CARE_E2E_PASSWORD ?? "VisualPass123!");
    await page.locator('input[placeholder="marstom"]').fill(process.env.CARE_E2E_CLINIC ?? "visual");
    await page.getByRole("button", { name: /sign in securely/i }).click();
    await expect(page.getByText("Your clinical day, in one place.")).toBeVisible();

    if (viewport.width <= 760) {
      await expect(page.getByRole("button", { name: "Open navigation" })).toBeVisible();
      await page.getByRole("button", { name: "Open navigation" }).click();
    }
    for (const label of ["Dashboard", "Patients & records", "OPG + AI", "Follow-up plans", "AI conversations", "Appointments", "Working hours"]) {
      if (viewport.width <= 760 && !(await page.getByRole("button", { name: label }).isVisible())) {
        await page.getByRole("button", { name: "Open navigation" }).click();
      }
      await page.getByRole("button", { name: label }).click();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `${label} overflows at ${viewport.width}px`).toBeLessThanOrEqual(1);
    }
  });
}
