import { describe, expect, it } from "vitest";
import { canonicalPresentationFixture } from "../src/fixtures";
import { applyEditOperation, EditOperationError } from "../src/index";

describe("structured edit operations", () => {
  it("updates an element without mutating the current document", () => {
    const original = structuredClone(canonicalPresentationFixture);
    const title = canonicalPresentationFixture.slides[0]?.elements[0];
    if (!title || title.type !== "text") throw new Error("Fixture title is missing");

    const next = applyEditOperation(canonicalPresentationFixture, {
      operationId: "operation-1",
      type: "upsert-element",
      slideId: "slide-title",
      element: {
        ...title,
        runs: [{ text: "A shorter title" }],
      },
    });

    expect(canonicalPresentationFixture).toEqual(original);
    expect(next.revision).toBe(1);
    expect(next.slides[0]?.revision).toBe(1);
    expect(next.slides[0]?.elements[0]).toMatchObject({
      id: "title",
      runs: [{ text: "A shorter title" }],
    });
  });

  it("moves a slide deterministically", () => {
    const second = {
      ...canonicalPresentationFixture.slides[0]!,
      id: "slide-second",
      title: "Second",
    };
    const deck = { ...canonicalPresentationFixture, slides: [...canonicalPresentationFixture.slides, second] };

    const next = applyEditOperation(deck, {
      operationId: "operation-2",
      type: "move-slide",
      slideId: "slide-second",
      index: 0,
    });

    expect(next.slides.map((slide) => slide.id)).toEqual(["slide-second", "slide-title"]);
  });

  it("does not silently ignore missing elements", () => {
    expect(() =>
      applyEditOperation(canonicalPresentationFixture, {
        operationId: "operation-3",
        type: "remove-element",
        slideId: "slide-title",
        elementId: "missing",
      }),
    ).toThrow(EditOperationError);
  });
});
