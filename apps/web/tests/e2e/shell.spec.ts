import { expect, test } from "@playwright/test";

test.describe("shell", () => {
  test("auth page renders editorial split-panel", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /bring your knowledge/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in|create account/i })).toBeVisible();
    await expect(page.locator(".u-skip-link")).toHaveCount(1);
  });

  test("dashboard requires auth and redirects to login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });

  test("register, then dashboard composer is interactive", async ({ page }) => {
    const email = `e2e-${Date.now()}@example.com`;
    await page.goto("/login");
    await page.getByRole("button", { name: /need an account/i }).click();
    await page.getByLabel("Email").fill(email);
    await page.getByRole("textbox", { name: "Password" }).fill("verysecurepassword123");
    await page.getByRole("button", { name: /create account/i }).click();
    await expect(page).toHaveURL(/\/$|\/dashboard/);

    await expect(page.getByRole("heading", { name: /what are we presenting/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /prompt/i })).toHaveAttribute("aria-selected", "true");

    // Theme picker has 4 cards
    const cards = page.getByRole("radio");
    await expect(cards).toHaveCount(4);

    // Select a non-default theme
    await page.getByRole("radio", { name: /warm studio/i }).click();
    await expect(page.getByRole("radio", { name: /warm studio/i })).toHaveAttribute("aria-checked", "true");

    // Theme toggle persists dark mode across reload
    await page.getByRole("button", { name: /switch to dark theme/i }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });
});
