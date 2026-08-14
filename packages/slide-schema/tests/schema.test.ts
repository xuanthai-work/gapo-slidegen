import { describe, expect, it } from "vitest";
import { canonicalPresentationFixture } from "../src/fixtures";
import {
  EDITOR_STAGE_HEIGHT,
  EDITOR_STAGE_WIDTH,
  parsePresentation,
  presentationSchema,
} from "../src/index";

describe("presentation schema", () => {
  it("round-trips the canonical editor fixture", () => {
    const parsed = parsePresentation(canonicalPresentationFixture);
    const reloaded = parsePresentation(JSON.parse(JSON.stringify(parsed)));

    expect(reloaded).toEqual(parsed);
    expect(EDITOR_STAGE_WIDTH / EDITOR_STAGE_HEIGHT).toBeCloseTo(16 / 9);
  });

  it("rejects more than 30 slides", () => {
    const result = presentationSchema.safeParse({
      ...canonicalPresentationFixture,
      slides: Array.from({ length: 31 }, (_, index) => ({
        ...canonicalPresentationFixture.slides[0],
        id: `slide-${index}`,
      })),
    });

    expect(result.success).toBe(false);
  });

  it("rejects an invalid image without a server-owned asset id", () => {
    const result = presentationSchema.safeParse({
      ...canonicalPresentationFixture,
      slides: [
        {
          ...canonicalPresentationFixture.slides[0],
          elements: [
            {
              id: "image",
              type: "image",
              position: { x: 0, y: 0 },
              size: { width: 100, height: 100 },
            },
          ],
        },
      ],
    });

    expect(result.success).toBe(false);
  });
});
