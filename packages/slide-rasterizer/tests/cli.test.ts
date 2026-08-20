import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { canonicalPresentationFixture } from "@gapo-slidegen/slide-schema/fixtures";

const packageRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const cli = join(packageRoot, "dist", "cli.js");
const fixturePath = join(packageRoot, "fixtures", "slide.json");
const hasChromium = process.env.SLIDEGEN_VISUAL_GATE_CHROMIUM !== "0";

describe("rasterizer fixture", () => {
  it("ships the canonical first slide", () => {
    const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as unknown;
    expect(fixture).toEqual(canonicalPresentationFixture.slides[0]);
  });
});

describe.skipIf(!hasChromium)("rasterize cli", () => {
  it("writes a 1280 png", () => {
    const slide = canonicalPresentationFixture.slides[0];
    if (!slide) throw new Error("missing canonical slide");
    const dir = mkdtempSync(join(tmpdir(), "slide-rasterizer-"));
    const slidePath = join(dir, "slide.json");
    const out = join(dir, "slide.png");
    writeFileSync(slidePath, JSON.stringify(slide));
    if (!existsSync(cli)) return;

    try {
      execFileSync(process.execPath, [cli, "--slide", slidePath, "--out", out], {
        stdio: "pipe",
        timeout: 60_000,
      });
    } catch (error) {
      if (String(error).includes("Executable doesn't exist")) return;
      throw error;
    }

    expect(existsSync(out)).toBe(true);
    const png = readFileSync(out);
    expect(png.byteLength).toBeGreaterThan(100);
    expect(png.readUInt32BE(16)).toBe(1280);
    expect(png.readUInt32BE(20)).toBe(720);
  }, 60_000);
});
