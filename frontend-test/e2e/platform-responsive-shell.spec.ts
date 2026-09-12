import { expect, test } from "@playwright/test";

const baseUrl = process.env.CARE_E2E_URL ?? "http://127.0.0.1:5173";
const publicRoutes = ["/", "/product", "/how-it-works", "/pricing", "/clinical-safety", "/about", "/login", "/register", "/privacy", "/terms", "/cookies", "/payments", "/clinical-disclaimer"];
const viewports = [
  { name: "phone", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "laptop", width: 1366, height: 768 },
  { name: "desktop", width: 1920, height: 1080 },
];

for (const viewport of viewports) {
  test(`${viewport.name}: public routes share responsive chrome`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.addInitScript(() => localStorage.setItem("teta2-product-language", "en"));

    for (const route of publicRoutes) {
      await page.goto(`${baseUrl}${route}`);
      await expect(page.locator(".t2-navbar")).toBeVisible();
      await expect(page.locator(".t2-footer")).toBeAttached();

      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `${route} has horizontal overflow at ${viewport.width}px`).toBeLessThanOrEqual(1);
    }
  });
}

test("first visit uses a compact flag-only language modal", async ({ page }) => {
  await page.goto(baseUrl);
  const modal = page.getByRole("dialog", { name: "Choose language" });
  await expect(modal).toBeVisible();
  await expect(modal.getByRole("button")).toHaveCount(3);
  await modal.getByRole("button", { name: "Русский" }).click();
  await expect(modal).toBeHidden();
  await expect.poll(() => page.evaluate(() => localStorage.getItem("teta2-product-language"))).toBe("ru");
});

test("essential storage notice is factual and links to its policy", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("teta2-product-language", "en"));
  await page.goto(baseUrl);
  const notice = page.getByLabel("Essential browser storage only");
  await expect(notice).toBeVisible();
  await expect(notice).toContainText("does not use advertising or analytics cookies");
  await notice.getByRole("button", { name: "Read policy" }).click();
  await expect(page).toHaveURL(/\/cookies$/);
});

test("laptop renders SVG flag and opens the downward language menu", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.addInitScript(() => localStorage.setItem("teta2-product-language", "en"));
  await page.goto(baseUrl);

  const trigger = page.locator(".t2-navbar .t2-language-trigger");
  await expect(trigger.locator(".t2-flag")).toBeVisible();
  await trigger.click();
  const menu = page.locator(".t2-navbar .t2-language-menu");
  await expect(menu).toBeVisible();
  await expect(menu.getByRole("menuitemradio")).toHaveCount(3);
  const positions = await Promise.all([trigger.boundingBox(), menu.boundingBox()]);
  expect(positions[0]).not.toBeNull();
  expect(positions[1]).not.toBeNull();
  expect(positions[1]!.y).toBeGreaterThan(positions[0]!.y);
});

test("mobile navigation preserves every shared destination", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => localStorage.setItem("teta2-product-language", "en"));
  await page.goto(baseUrl);
  await page.getByRole("button", { name: "Open navigation" }).click();
  const navigation = page.getByRole("navigation", { name: "Primary navigation" });
  for (const label of ["Product", "How it works", "Pricing", "Clinical & Safety", "About / Contact", "Sign in", "Request access"]) {
    await expect(navigation.getByRole("button", { name: label, exact: true })).toBeVisible();
  }
});
