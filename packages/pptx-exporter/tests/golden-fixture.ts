import type { Presentation } from "@gapo-slidegen/slide-schema";
import { canonicalPresentationFixture } from "@gapo-slidegen/slide-schema/fixtures";

export const GOLDEN_IMAGE_DATA =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII=";

const firstSlide = canonicalPresentationFixture.slides[0];

if (!firstSlide) {
  throw new Error("Canonical fixture must contain a slide.");
}

export const exportGoldenFixture: Presentation = {
  ...canonicalPresentationFixture,
  id: "pptx-export-golden",
  title: "Native object export proof",
  slides: [
    {
      ...firstSlide,
      id: "native-elements",
      elements: [
        ...firstSlide.elements,
        {
          id: "metrics-table",
          type: "table",
          position: { x: 96, y: 400 },
          size: { width: 480, height: 190 },
          rotation: 0,
          opacity: 1,
          locked: false,
          decorative: false,
          rows: [
            [
              { runs: [{ text: "Metric" }], horizontalAlign: "left" },
              { runs: [{ text: "Result" }], horizontalAlign: "right" },
            ],
            [
              { runs: [{ text: "Activation" }], horizontalAlign: "left" },
              { runs: [{ text: "72%" }], horizontalAlign: "right" },
            ],
          ],
          columnWidths: [300, 180],
          rowHeights: [64, 64],
        },
        {
          id: "adoption-chart",
          type: "chart",
          position: { x: 640, y: 90 },
          size: { width: 500, height: 300 },
          rotation: 0,
          opacity: 1,
          locked: false,
          decorative: false,
          chartType: "bar",
          categories: ["Apr", "May", "Jun"],
          series: [{ name: "Active teams", values: [12, 19, 31] }],
          colors: ["#285FC7"],
          showLegend: true,
        },
        {
          id: "uploaded-image",
          type: "image",
          position: { x: 960, y: 450 },
          size: { width: 120, height: 120 },
          rotation: 0,
          opacity: 1,
          locked: false,
          decorative: false,
          assetId: "golden-pixel",
          fit: "fill",
          focusX: 0.5,
          focusY: 0.5,
          cropScale: 1,
          flipHorizontal: false,
          flipVertical: false,
          alt: "Uploaded image fixture",
        },
      ],
    },
  ],
};
