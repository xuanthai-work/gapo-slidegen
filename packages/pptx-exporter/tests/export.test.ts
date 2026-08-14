import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import JSZip from "jszip";
import { describe, expect, it } from "vitest";
import { exportPresentationToPptx } from "../src/index";
import { exportGoldenFixture, GOLDEN_IMAGE_DATA } from "./golden-fixture";

describe("schema-native PPTX exporter", () => {
  it("exports editable OOXML objects instead of a rasterized slide", async () => {
    const result = await exportPresentationToPptx(exportGoldenFixture, {
      resolveAsset: (assetId) =>
        assetId === "golden-pixel" ? { data: GOLDEN_IMAGE_DATA } : null,
    });

    expect(result.buffer.subarray(0, 2).toString()).toBe("PK");
    expect(result.warnings).toEqual([]);

    const archive = await JSZip.loadAsync(result.buffer);
    const slideXml = await archive.file("ppt/slides/slide1.xml")?.async("text");
    const slideRelations = await archive
      .file("ppt/slides/_rels/slide1.xml.rels")
      ?.async("text");
    const chartXml = await archive.file("ppt/charts/chart1.xml")?.async("text");

    expect(slideXml).toContain("Quarterly product review");
    expect(slideXml).toContain("<p:sp>");
    expect(slideXml).toContain("<a:tbl>");
    expect(slideRelations).toContain("/ppt/charts/chart1.xml");
    expect(chartXml).toContain("Active teams");
    expect(chartXml).toContain("<c:chartSpace");
    expect(
      Object.keys(archive.files).some((path) => path.startsWith("ppt/media/image")),
    ).toBe(true);

    if (process.env.WRITE_GOLDEN_PPTX === "1") {
      const outputDirectory = resolve(process.cwd(), "../../.data/export-spike");
      await mkdir(outputDirectory, { recursive: true });
      await writeFile(resolve(outputDirectory, "native-elements-golden.pptx"), result.buffer);
    }
  });

  it("reports an unresolved image instead of silently inventing a fallback", async () => {
    const result = await exportPresentationToPptx(exportGoldenFixture);

    expect(result.warnings).toContainEqual(
      expect.objectContaining({
        code: "asset-missing",
        elementId: "uploaded-image",
      }),
    );
  });
});
