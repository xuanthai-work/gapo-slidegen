import { describe, expect, it, vi } from "vitest";
import { canonicalPresentationFixture } from "@gapo-slidegen/slide-schema/fixtures";
import { EditorBoundary } from "../src/index";

describe("editor product boundary", () => {
  it("validates input and emits a persistence-friendly change", () => {
    const onChange = vi.fn();
    const editor = new EditorBoundary({
      initialDocument: canonicalPresentationFixture,
      onChange,
    });
    const title = editor.document.slides[0]?.elements[0];
    if (!title || title.type !== "text") throw new Error("Fixture title is missing");

    const document = editor.apply({
      operationId: "edit-title",
      type: "upsert-element",
      slideId: "slide-title",
      element: { ...title, runs: [{ text: "Edited in the boundary" }] },
    });

    expect(document.revision).toBe(1);
    expect(onChange).toHaveBeenCalledOnce();
    expect(onChange.mock.calls[0]?.[0].document).toEqual(document);
  });

  it("rejects persisted data that does not match the canonical contract", () => {
    expect(
      () => new EditorBoundary({ initialDocument: { id: "broken" }, onChange: vi.fn() }),
    ).toThrow();
  });
});
