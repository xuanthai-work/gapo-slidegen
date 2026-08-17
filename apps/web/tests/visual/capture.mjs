import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const OUT = path.resolve("./tests/visual/baselines");
await mkdir(OUT, { recursive: true });

const browser = await chromium.launch();

// Context 1: unauthenticated, for auth screens (login + register)
const authContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
const authPage = await authContext.newPage();

// Context 2: authenticated via registration, for dashboard + editor screens
const dashContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
const dashPage = await dashContext.newPage();

// Register a fresh user in the dashboard context (Path A)
const stamp = Date.now();
const email = `visual-${stamp}@example.com`;
const password = "verysecurepassword123";
await dashPage.goto("http://localhost:3000/login");
await dashPage.click("button:has-text('Need an account?')");
await dashPage.locator("#email").fill(email);
await dashPage.getByRole("textbox", { name: "Password" }).fill(password);
await dashPage.click("button:has-text('Create account')");
await dashPage.waitForURL(/\/$|\/dashboard/, { timeout: 10_000 });

const authTargets = [
  { name: "01-auth-login.png", url: "/login", waitFor: "h1" },
  { name: "02-auth-register.png", url: "/login", waitFor: "button:has-text('Need an account?')", click: "button:has-text('Need an account?')" },
];

for (const target of authTargets) {
  console.log(`Capturing ${target.name}…`);
  await authPage.goto(`http://localhost:3000${target.url}`);
  await authPage.waitForSelector(target.waitFor, { timeout: 10_000 });
  if (target.click) {
    await authPage.click(target.click);
  }
  // Allow fonts to settle
  await authPage.waitForTimeout(800);
  await authPage.screenshot({ path: path.join(OUT, target.name), fullPage: false });
  console.log(`  saved ${target.name}`);
}

const dashTargets = [
  { name: "03-dashboard-blank.png", url: "/", waitFor: "h1" },
  { name: "04-dashboard-template-picker.png", url: "/", waitFor: "[role=radio]" },
];

for (const target of dashTargets) {
  console.log(`Capturing ${target.name}…`);
  await dashPage.goto(`http://localhost:3000${target.url}`);
  await dashPage.waitForSelector(target.waitFor, { timeout: 10_000 });
  // Allow fonts to settle
  await dashPage.waitForTimeout(800);
  await dashPage.screenshot({ path: path.join(OUT, target.name), fullPage: false });
  console.log(`  saved ${target.name}`);
}

// Generate a presentation and capture editor/present/palette/toast states
console.log("Generating a presentation for editor captures…");
await dashPage.goto("http://localhost:3000/");
await dashPage.waitForSelector("#composer-text", { timeout: 10_000 });
await dashPage.locator("#composer-text").fill("visual regression topic");
await dashPage.getByRole("button", { name: /generate presentation/i }).click();
await dashPage.waitForURL(/\/editor\?presentation=/, { timeout: 30_000 });
await dashPage.waitForSelector('aside[aria-label="Slides"] .thumbnail', { timeout: 10_000 });
await dashPage.waitForTimeout(800);

// 05-editor-shell.png — already on editor page
console.log("Capturing 05-editor-shell.png…");
await dashPage.waitForTimeout(800);
await dashPage.screenshot({ path: path.join(OUT, "05-editor-shell.png"), fullPage: false });
console.log("  saved 05-editor-shell.png");

// 06-editor-present-mode.png
console.log("Capturing 06-editor-present-mode.png…");
await dashPage.getByRole("button", { name: /present/i }).click();
await dashPage.waitForSelector('section[aria-label="Presentation mode"]', { timeout: 10_000 });
await dashPage.waitForTimeout(500);
await dashPage.screenshot({ path: path.join(OUT, "06-editor-present-mode.png"), fullPage: false });
console.log("  saved 06-editor-present-mode.png");
await dashPage.keyboard.press("Escape");
await dashPage.waitForSelector('section[aria-label="Presentation mode"]', { state: "hidden", timeout: 5_000 });

// Capture command palette open
console.log("Capturing 07-editor-command-palette.png…");
await dashPage.keyboard.press("Control+k");
await dashPage.waitForSelector('[role="dialog"][aria-label="Command palette"]', { timeout: 5_000 });
await dashPage.waitForTimeout(800);
await dashPage.screenshot({ path: path.join(OUT, "07-editor-command-palette.png"), fullPage: false });
console.log("  saved 07-editor-command-palette.png");
await dashPage.keyboard.press("Escape");

// Capture toast notification
console.log("Capturing 08-editor-toast.png…");
await dashPage.getByRole("button", { name: /export pptx/i }).click();
await dashPage.waitForSelector(".toast-region", { timeout: 10_000 });
await dashPage.waitForTimeout(400);
await dashPage.screenshot({ path: path.join(OUT, "08-editor-toast.png"), fullPage: false });
console.log("  saved 08-editor-toast.png");

await browser.close();
console.log("Visual baselines captured.");
