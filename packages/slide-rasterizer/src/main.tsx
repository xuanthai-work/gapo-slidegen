import { createRoot } from "react-dom/client";
import { SlideCanvas } from "@gapo-slidegen/slide-editor/canvas";
import { EDITOR_STAGE_HEIGHT, EDITOR_STAGE_WIDTH, type Slide } from "@gapo-slidegen/slide-schema";

const root = document.getElementById("root");
if (!root) throw new Error("missing root");
root.style.width = `${EDITOR_STAGE_WIDTH}px`;
root.style.height = `${EDITOR_STAGE_HEIGHT}px`;
root.style.overflow = "hidden";

const response = await fetch("./slide.json");
if (!response.ok) throw new Error("failed to load slide.json");
const slide = (await response.json()) as Slide;

createRoot(root).render(
  <SlideCanvas
    elements={slide.elements ?? []}
    background={slide.background ?? "#FFFFFF"}
    selectedElementId={null}
    onSelectElement={() => undefined}
    onChangeElement={() => undefined}
    readOnly
  />,
);
