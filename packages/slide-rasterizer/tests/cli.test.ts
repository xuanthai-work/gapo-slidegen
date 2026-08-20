import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { canonicalPresentationFixture } from "@gapo-slidegen/slide-schema/fixtures";

const execFileAsync = promisify(execFile);
const packageRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const cli = join(packageRoot, "dist", "cli.js");
const fixturePath = join(packageRoot, "fixtures", "slide.json");
const hasChromium = process.env.SLIDEGEN_VISUAL_GATE_CHROMIUM !== "0";

function writeSlide(dir: string, name: string, slide: unknown): string {
  const slidePath = join(dir, name);
  writeFileSync(slidePath, JSON.stringify(slide));
  return slidePath;
}

async function rasterize(slidePath: string, out: string): Promise<void> {
  await execFileAsync(process.execPath, [cli, "--slide", slidePath, "--out", out], {
    timeout: 60_000,
  });
}

function isMissingChromium(error: unknown): boolean {
  return String(error).includes("Executable doesn't exist");
}

describe("rasterizer fixture", () => {
  it("ships the canonical first slide", () => {
    const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as unknown;
    expect(fixture).toEqual(canonicalPresentationFixture.slides[0]);
  });
});

describe.skipIf(!hasChromium)("rasterize cli", () => {
  it("fails when the CLI artifact is missing", () => {
    expect(existsSync(cli)).toBe(true);
  });

  it("writes a 1280 png", async (ctx) => {
    const slide = canonicalPresentationFixture.slides[0];
    if (!slide) throw new Error("missing canonical slide");
    const dir = mkdtempSync(join(tmpdir(), "slide-rasterizer-"));
    const slidePath = writeSlide(dir, "slide.json", slide);
    const out = join(dir, "slide.png");

    try {
      await rasterize(slidePath, out);
    } catch (error) {
      if (isMissingChromium(error)) {
        ctx.skip();
        return;
      }
      throw error;
    }

    expect(existsSync(out)).toBe(true);
    const png = readFileSync(out);
    expect(png.byteLength).toBeGreaterThan(100);
    expect(png.readUInt32BE(16)).toBe(1280);
    expect(png.readUInt32BE(20)).toBe(720);
  }, 60_000);

  it("isolates concurrent slide json inputs", async (ctx) => {
    const slide = canonicalPresentationFixture.slides[0];
    if (!slide) throw new Error("missing canonical slide");
    expect(existsSync(cli)).toBe(true);
    const dir = mkdtempSync(join(tmpdir(), "slide-rasterizer-"));
    const slideA = writeSlide(dir, "a.json", { ...slide, background: "#FFFFFF" });
    const slideB = writeSlide(dir, "b.json", { ...slide, background: "#000000" });
    const outA = join(dir, "a.png");
    const outB = join(dir, "b.png");

    try {
      await Promise.all([rasterize(slideA, outA), rasterize(slideB, outB)]);
    } catch (error) {
      if (isMissingChromium(error)) {
        ctx.skip();
        return;
      }
      throw error;
    }

    const pngA = readFileSync(outA);
    const pngB = readFileSync(outB);
    expect(pngA.byteLength).toBeGreaterThan(100);
    expect(pngB.byteLength).toBeGreaterThan(100);
    expect(pngA.equals(pngB)).toBe(false);
  }, 120_000);
});
