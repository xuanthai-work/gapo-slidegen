import { expect, test } from "@playwright/test";

test.describe("editor", () => {
  test("register, generate, present, command palette, and toast", async ({ page }) => {
    const email = `e2e-${Date.now()}@example.com`;
    const password = "verysecurepassword123";

    await test.step("register and create a presentation", async () => {
      await page.goto("/login");
      await page.getByRole("button", { name: /need an account/i }).click();
      await page.getByLabel("Email").fill(email);
      await page.getByRole("textbox", { name: "Password" }).fill(password);
      await page.getByRole("button", { name: /create account/i }).click();
      await expect(page).toHaveURL(/\/$|\/dashboard/);

      await expect(page.getByRole("heading", { name: /what are we presenting/i })).toBeVisible();
      await expect(page.getByRole("tab", { name: /prompt/i })).toHaveAttribute("aria-selected", "true");

      await page.locator("#composer-text").fill("product launch tips");
      await page.getByRole("button", { name: /generate presentation/i }).click();

      await expect(page).toHaveURL(/\/editor\?presentation=/, { timeout: 30_000 });
      await expect(page.locator("header.topbar")).toBeVisible();
      await expect(page.locator('aside[aria-label="Slides"]')).toBeVisible();
      await expect(page.locator('section[aria-label="Slide canvas"]')).toBeVisible();
      await expect(page.locator("aside.properties")).toBeVisible();
    });

    await test.step("present mode navigation", async () => {
      await page.getByRole("button", { name: /present/i }).click();
      const presentOverlay = page.locator('section[aria-label="Presentation mode"]');
      await expect(presentOverlay).toBeVisible();

      const counter = presentOverlay.locator(".present-controls span");
      await expect(counter).toHaveText(/^1 \/ \d+$/);

      await page.keyboard.press("ArrowRight");
      await expect(counter).toHaveText(/^2 \/ \d+$/);

      await page.keyboard.press("Escape");
      await expect(presentOverlay).toBeHidden();
    });

    await test.step("command palette", async () => {
      await page.keyboard.press("Control+k");
      const palette = page.getByRole("dialog", { name: "Command palette" });
      await expect(palette).toBeVisible();
      const searchInput = palette.getByRole("textbox", { name: "Search commands" });
      await expect(searchInput).toBeVisible();

      await searchInput.fill("present");
      const presentCommand = palette.locator(".command-palette__item").filter({ hasText: "Present" });
      await expect(presentCommand).toBeVisible();
      await page.keyboard.press("Enter");

      await expect(page.locator('section[aria-label="Presentation mode"]')).toBeVisible();
      await page.keyboard.press("Escape");
    });

    await test.step("toast notification", async () => {
      const exportButton = page.getByRole("button", { name: /export pptx/i });
      await exportButton.click();
      await expect(page.locator(".toast-region")).toBeVisible();
      await expect(page.getByText("Presentation exported")).toBeVisible();
    });
  });
});
