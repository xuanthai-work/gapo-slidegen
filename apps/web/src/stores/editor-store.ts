import type { OutlineItem } from "@gapo-slidegen/contracts";
import { create } from "zustand";

interface EditorState {
  selectedSlideId: string | null;
  outline: OutlineItem[];
  selectSlide: (slideId: string | null) => void;
  setOutline: (outline: OutlineItem[]) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  selectedSlideId: null,
  outline: [],
  selectSlide: (selectedSlideId) => set({ selectedSlideId }),
  setOutline: (outline) => set({ outline }),
}));
