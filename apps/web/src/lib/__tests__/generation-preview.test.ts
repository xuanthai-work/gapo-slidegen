import { describe, expect, it } from "vitest";
import {
  applyGenerationEvent,
  emptyGenerationPreview,
  type GenerationPreviewEvent,
} from "../generation-preview";

function event(partial: Partial<GenerationPreviewEvent>): GenerationPreviewEvent {
  return {
    version: 1,
    type: "slot.snapshot",
    job_id: "job-1",
    attempt: 1,
    sequence: 1,
    slide_id: "slide-1",
    slot: "title",
    data: { value: "A" },
    ...partial,
  };
}

describe("applyGenerationEvent", () => {
  it("replaces snapshots instead of appending them", () => {
    let state = emptyGenerationPreview();
    state = applyGenerationEvent(state, event({ sequence: 1, data: { value: "A" } }));
    state = applyGenerationEvent(state, event({ sequence: 2, data: { value: "AB" } }));
    expect(state.slides).toHaveLength(1);
    expect(state.slides[0]?.slots.title).toBe("AB");
  });

  it("ignores stale attempts and sequences", () => {
    let state = applyGenerationEvent(emptyGenerationPreview(), event({ attempt: 2, sequence: 4, data: { value: "New" } }));
    state = applyGenerationEvent(state, event({ attempt: 1, sequence: 9, data: { value: "Old" } }));
    state = applyGenerationEvent(state, event({ attempt: 2, sequence: 3, data: { value: "Stale" } }));
    expect(state.slides[0]?.slots.title).toBe("New");
  });

  it("keeps completed slides when a later attempt fills the remainder", () => {
    let state = applyGenerationEvent(
      emptyGenerationPreview(),
      event({ slide_id: "cover", attempt: 1, sequence: 1, data: { value: "Cover" } }),
    );
    state = applyGenerationEvent(
      state,
      event({ slide_id: "point-1", attempt: 2, sequence: 1, data: { value: "Point" } }),
    );
    expect(state.slides).toHaveLength(2);
    expect(state.slides.find((slide) => slide.slideId === "cover")?.slots.title).toBe("Cover");
    expect(state.slides.find((slide) => slide.slideId === "point-1")?.slots.title).toBe("Point");
  });
});
