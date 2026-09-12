import { expect, test } from "@playwright/test";

test("Request access opens the live clinic application without a refresh", async ({ page }) => {
  await page.goto(process.env.CARE_E2E_URL ?? "http://127.0.0.1:5173/");

  const english = page.getByRole("button", { name: /Continue in English/i });
  if (await english.isVisible()) await english.click();

  await page.getByRole("button", { name: /^Request access$/i }).first().click();

  await expect(page).toHaveURL(/\/register$/);
  await expect(page.getByRole("heading", { name: "Access request", exact: true })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Clinic name *", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Request access to Teta2" })).toBeHidden();
});
