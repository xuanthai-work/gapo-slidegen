export type TemplateId =
  | "modern"
  | "editorial"
  | "executive"
  | "swift"
  | "standard"
  | "momentum"
  | "general"
  | "dynamic";

export type ColorSchemeId =
  | "edge-yellow"
  | "light-rose"
  | "mint-blue"
  | "professional-blue"
  | "professional-dark";

export type TemplateOption = {
  id: TemplateId;
  name: string;
  pitch: string;
};

export type ColorSchemeOption = {
  id: ColorSchemeId;
  name: string;
  paper: string;
  ink: string;
  accent: string;
};

export const PRESENTON_TEMPLATES: TemplateOption[] = [
  { id: "modern", name: "Modern", pitch: "Clean title, grids, and icon lists" },
  { id: "editorial", name: "Editorial", pitch: "Magazine collage and long-form type" },
  { id: "executive", name: "Executive", pitch: "Centered leadership covers" },
  { id: "swift", name: "Swift", pitch: "Split cover and stacked cards" },
  { id: "standard", name: "Standard", pitch: "Image-led business pages" },
  { id: "momentum", name: "Momentum", pitch: "Waves, process, and motion" },
  { id: "general", name: "General", pitch: "Straightforward intro and lists" },
  { id: "dynamic", name: "Dynamic", pitch: "Bold cover and visual columns" },
];

export const PRESENTON_COLOR_SCHEMES: ColorSchemeOption[] = [
  { id: "professional-blue", name: "Professional Blue", paper: "#FFFFFF", ink: "#161616", accent: "#DAE6FF" },
  { id: "professional-dark", name: "Professional Dark", paper: "#050505", ink: "#EFF5F1", accent: "#424242" },
  { id: "mint-blue", name: "Mint Blue", paper: "#FFFFFF", ink: "#3B3172", accent: "#80E7CF" },
  { id: "edge-yellow", name: "Edge Yellow", paper: "#1F1F1F", ink: "#F5F547", accent: "#424242" },
  { id: "light-rose", name: "Light Rose", paper: "#F69C9C", ink: "#030202", accent: "#FFAEB4" },
];

export const DEFAULT_TEMPLATE_ID: TemplateId = "modern";
export const DEFAULT_COLOR_SCHEME_ID: ColorSchemeId = "professional-blue";
