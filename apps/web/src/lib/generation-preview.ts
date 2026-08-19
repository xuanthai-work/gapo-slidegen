export type GenerationPreviewEvent = {
  version: number;
  type: string;
  job_id: string;
  attempt: number;
  sequence: number;
  slide_id: string;
  slot: string | null;
  data: {
    value?: string;
    content?: { title?: string; slots?: Record<string, unknown> };
  };
};

export type PreviewSlide = {
  slideId: string;
  attempt: number;
  sequence: number;
  slots: Record<string, string>;
};

export type GenerationPreviewState = {
  attempt: number;
  slides: PreviewSlide[];
};

export const emptyGenerationPreview = (): GenerationPreviewState => ({
  attempt: 1,
  slides: [],
});

export function applyGenerationEvent(
  state: GenerationPreviewState,
  event: GenerationPreviewEvent,
): GenerationPreviewState {
  const nextAttempt = Math.max(state.attempt, event.attempt);
  const current = state.slides.find((slide) => slide.slideId === event.slide_id);
  if (current) {
    if (event.attempt < current.attempt) {
      return { ...state, attempt: nextAttempt };
    }
    if (event.attempt === current.attempt && event.sequence < current.sequence) {
      return { ...state, attempt: nextAttempt };
    }
  }
  const slots = current && event.attempt === current.attempt ? { ...current.slots } : {};
  if (event.type === "slot.snapshot" && event.slot && typeof event.data.value === "string") {
    slots[event.slot] = event.data.value;
  }
  if (event.type === "slide.completed") {
    const title = event.data.content?.title;
    if (typeof title === "string") {
      slots.title = title;
    }
    const contentSlots = event.data.content?.slots;
    if (contentSlots && typeof contentSlots === "object") {
      for (const [name, value] of Object.entries(contentSlots)) {
        if (typeof value === "string") {
          slots[name] = value;
        }
      }
    }
  }
  const updated: PreviewSlide = {
    slideId: event.slide_id,
    attempt: event.attempt,
    sequence: event.sequence,
    slots,
  };
  const remaining = state.slides.filter((slide) => slide.slideId !== event.slide_id);
  remaining.push(updated);
  return { attempt: nextAttempt, slides: remaining };
}
