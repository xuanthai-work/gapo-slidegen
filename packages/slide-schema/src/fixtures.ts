import {
  EDITOR_STAGE_HEIGHT,
  EDITOR_STAGE_WIDTH,
  SLIDE_SCHEMA_VERSION,
  type Presentation,
} from "./schema";

export const canonicalPresentationFixture: Presentation = {
  id: "presentation-fixture",
  schemaVersion: SLIDE_SCHEMA_VERSION,
  title: "Product review",
  language: "en",
  revision: 0,
  theme: {
    id: "theme-fixture",
    name: "Editorial cobalt",
    colors: {
      background: "#F4F6F9",
      surface: "#FFFFFF",
      primary: "#285FC7",
      secondary: "#172033",
      accent: "#285FC7",
      text: "#172033",
      muted: "#778296",
    },
    fonts: {
      heading: "Be Vietnam Pro",
      body: "Be Vietnam Pro",
    },
  },
  slides: [
    {
      id: "slide-title",
      title: "Quarterly product review",
      background: "#FFFFFF",
      revision: 0,
      elements: [
        {
          id: "title",
          type: "text",
          position: { x: 96, y: 104 },
          size: { width: 760, height: 180 },
          rotation: 0,
          opacity: 1,
          locked: false,
          decorative: false,
          runs: [{ text: "Quarterly product review" }],
          horizontalAlign: "left",
          verticalAlign: "top",
        },
        {
          id: "accent-shape",
          type: "shape",
          position: { x: 96, y: 330 },
          size: { width: 420, height: 18 },
          rotation: 0,
          opacity: 1,
          locked: false,
          decorative: true,
          shape: "rectangle",
          fill: { color: "#285FC7", opacity: 1 },
          cornerRadius: 9,
        },
      ],
    },
  ],
};

export const editorStage = {
  width: EDITOR_STAGE_WIDTH,
  height: EDITOR_STAGE_HEIGHT,
};
