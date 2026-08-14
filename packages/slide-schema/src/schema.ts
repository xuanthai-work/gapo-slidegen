import { z } from "zod";

export const SLIDE_SCHEMA_VERSION = 1 as const;
export const EDITOR_STAGE_WIDTH = 1280 as const;
export const EDITOR_STAGE_HEIGHT = 720 as const;

const finiteNumber = z.number().finite();
const nonNegativeNumber = finiteNumber.nonnegative();
const normalizedNumber = finiteNumber.min(0).max(1);
const entityId = z.string().trim().min(1).max(160);
const color = z.string().trim().min(1).max(128);

export const positionSchema = z.object({
  x: finiteNumber,
  y: finiteNumber,
});

export const sizeSchema = z.object({
  width: nonNegativeNumber,
  height: nonNegativeNumber,
});

export const paddingSchema = z.object({
  top: nonNegativeNumber,
  right: nonNegativeNumber,
  bottom: nonNegativeNumber,
  left: nonNegativeNumber,
});

export const fontSchema = z.object({
  family: z.string().trim().min(1).optional(),
  size: nonNegativeNumber.optional(),
  color: color.optional(),
  bold: z.boolean().optional(),
  italic: z.boolean().optional(),
  underline: z.boolean().optional(),
  lineHeight: nonNegativeNumber.optional(),
  letterSpacing: finiteNumber.optional(),
});

export const textRunSchema = z.object({
  text: z.string(),
  font: fontSchema.optional(),
});

export const elementBaseSchema = z.object({
  id: entityId,
  position: positionSchema,
  size: sizeSchema,
  rotation: finiteNumber.default(0),
  opacity: normalizedNumber.default(1),
  locked: z.boolean().default(false),
  name: z.string().trim().min(1).max(200).optional(),
  decorative: z.boolean().default(false),
  groupId: entityId.optional(),
  componentId: entityId.optional(),
  componentSlot: z.string().trim().min(1).max(160).optional(),
});

const fillSchema = z.object({
  color,
  opacity: normalizedNumber.default(1),
});

const strokeSchema = z.object({
  color,
  width: nonNegativeNumber,
  opacity: normalizedNumber.default(1),
  dash: z.array(nonNegativeNumber).optional(),
});

const textElementSchema = elementBaseSchema.extend({
  type: z.literal("text"),
  runs: z.array(textRunSchema),
  font: fontSchema.optional(),
  horizontalAlign: z.enum(["left", "center", "right"]).default("left"),
  verticalAlign: z.enum(["top", "middle", "bottom"]).default("top"),
  fill: fillSchema.optional(),
  stroke: strokeSchema.optional(),
});

const textListElementSchema = elementBaseSchema.extend({
  type: z.literal("text-list"),
  items: z.array(z.array(textRunSchema)),
  marker: z.enum(["bullet", "number", "none"]).default("bullet"),
  font: fontSchema.optional(),
});

const imageElementSchema = elementBaseSchema.extend({
  type: z.literal("image"),
  assetId: entityId,
  fit: z.enum(["contain", "cover", "fill"]).default("cover"),
  focusX: normalizedNumber.default(0.5),
  focusY: normalizedNumber.default(0.5),
  cropScale: nonNegativeNumber.default(1),
  flipHorizontal: z.boolean().default(false),
  flipVertical: z.boolean().default(false),
  alt: z.string().max(1_000).default(""),
});

const shapeElementSchema = elementBaseSchema.extend({
  type: z.literal("shape"),
  shape: z.enum(["rectangle", "ellipse", "triangle", "diamond"]),
  fill: fillSchema.optional(),
  stroke: strokeSchema.optional(),
  cornerRadius: nonNegativeNumber.default(0),
});

const lineElementSchema = elementBaseSchema.extend({
  type: z.literal("line"),
  stroke: strokeSchema,
  startArrow: z.boolean().default(false),
  endArrow: z.boolean().default(false),
});

const tableCellSchema = z.object({
  runs: z.array(textRunSchema),
  font: fontSchema.optional(),
  fill: fillSchema.optional(),
  horizontalAlign: z.enum(["left", "center", "right"]).default("left"),
});

const tableElementSchema = elementBaseSchema.extend({
  type: z.literal("table"),
  rows: z.array(z.array(tableCellSchema)).min(1),
  columnWidths: z.array(nonNegativeNumber).optional(),
  rowHeights: z.array(nonNegativeNumber).optional(),
});

const chartSeriesSchema = z.object({
  name: z.string(),
  values: z.array(finiteNumber),
});

const chartElementSchema = elementBaseSchema.extend({
  type: z.literal("chart"),
  chartType: z.enum([
    "area",
    "bar",
    "donut",
    "horizontal-bar",
    "line",
    "pie",
    "radar",
    "scatter",
    "stacked-bar",
  ]),
  categories: z.array(z.string()),
  series: z.array(chartSeriesSchema).min(1),
  colors: z.array(color).optional(),
  showLegend: z.boolean().default(true),
});

const svgElementSchema = elementBaseSchema.extend({
  type: z.literal("svg"),
  svg: z.string().min(1),
  alt: z.string().max(1_000).default(""),
});

type ElementBase = z.infer<typeof elementBaseSchema>;
type Fill = z.infer<typeof fillSchema>;
type Stroke = z.infer<typeof strokeSchema>;
type Padding = z.infer<typeof paddingSchema>;
type TableCell = z.infer<typeof tableCellSchema>;
type ChartSeries = z.infer<typeof chartSeriesSchema>;

export type TextElement = ElementBase & {
  type: "text";
  runs: TextRun[];
  font?: Font;
  horizontalAlign: "left" | "center" | "right";
  verticalAlign: "top" | "middle" | "bottom";
  fill?: Fill;
  stroke?: Stroke;
};

export type TextListElement = ElementBase & {
  type: "text-list";
  items: TextRun[][];
  marker: "bullet" | "number" | "none";
  font?: Font;
};

export type ImageElement = ElementBase & {
  type: "image";
  assetId: string;
  fit: "contain" | "cover" | "fill";
  focusX: number;
  focusY: number;
  cropScale: number;
  flipHorizontal: boolean;
  flipVertical: boolean;
  alt: string;
};

export type ShapeElement = ElementBase & {
  type: "shape";
  shape: "rectangle" | "ellipse" | "triangle" | "diamond";
  fill?: Fill;
  stroke?: Stroke;
  cornerRadius: number;
};

export type LineElement = ElementBase & {
  type: "line";
  stroke: Stroke;
  startArrow: boolean;
  endArrow: boolean;
};

export type TableElement = ElementBase & {
  type: "table";
  rows: TableCell[][];
  columnWidths?: number[];
  rowHeights?: number[];
};

export type ChartElement = ElementBase & {
  type: "chart";
  chartType:
    | "area"
    | "bar"
    | "donut"
    | "horizontal-bar"
    | "line"
    | "pie"
    | "radar"
    | "scatter"
    | "stacked-bar";
  categories: string[];
  series: ChartSeries[];
  colors?: string[];
  showLegend: boolean;
};

export type SvgElement = ElementBase & {
  type: "svg";
  svg: string;
  alt: string;
};

export type GroupElement = ElementBase & {
  type: "group";
  children: SlideElement[];
};

export type ContainerElement = ElementBase & {
  type: "container";
  child: SlideElement | null;
  fill?: Fill;
  stroke?: Stroke;
  padding?: Padding;
};

export type FlexElement = ElementBase & {
  type: "flex";
  direction: "row" | "column";
  children: SlideElement[];
  gap: number;
  padding?: Padding;
};

export type GridElement = ElementBase & {
  type: "grid";
  columns: number;
  children: SlideElement[];
  gap: number;
  padding?: Padding;
};

export type SlideElement =
  | TextElement
  | TextListElement
  | ImageElement
  | ShapeElement
  | LineElement
  | TableElement
  | ChartElement
  | SvgElement
  | GroupElement
  | ContainerElement
  | FlexElement
  | GridElement;

export const slideElementSchema = z.lazy(() =>
  z.discriminatedUnion("type", [
    textElementSchema,
    textListElementSchema,
    imageElementSchema,
    shapeElementSchema,
    lineElementSchema,
    tableElementSchema,
    chartElementSchema,
    svgElementSchema,
    elementBaseSchema.extend({
      type: z.literal("group"),
      children: z.array(slideElementSchema),
    }),
    elementBaseSchema.extend({
      type: z.literal("container"),
      child: slideElementSchema.nullable().default(null),
      fill: fillSchema.optional(),
      stroke: strokeSchema.optional(),
      padding: paddingSchema.optional(),
    }),
    elementBaseSchema.extend({
      type: z.literal("flex"),
      direction: z.enum(["row", "column"]),
      children: z.array(slideElementSchema),
      gap: nonNegativeNumber.default(0),
      padding: paddingSchema.optional(),
    }),
    elementBaseSchema.extend({
      type: z.literal("grid"),
      columns: z.number().int().positive(),
      children: z.array(slideElementSchema),
      gap: nonNegativeNumber.default(0),
      padding: paddingSchema.optional(),
    }),
  ]),
) as z.ZodType<SlideElement>;

export const themeSchema = z.object({
  id: entityId,
  name: z.string().trim().min(1).max(160),
  colors: z.object({
    background: color,
    surface: color,
    primary: color,
    secondary: color,
    accent: color,
    text: color,
    muted: color,
  }),
  fonts: z.object({
    heading: z.string().trim().min(1),
    body: z.string().trim().min(1),
  }),
});

export const slideSchema = z.object({
  id: entityId,
  title: z.string().max(500).default(""),
  background: color.default("#FFFFFF"),
  elements: z.array(slideElementSchema),
  revision: z.number().int().nonnegative().default(0),
});

export const presentationSchema = z.object({
  id: entityId,
  schemaVersion: z.literal(SLIDE_SCHEMA_VERSION),
  title: z.string().trim().min(1).max(500),
  language: z.string().trim().min(2).max(32),
  theme: themeSchema,
  slides: z.array(slideSchema).max(30),
  revision: z.number().int().nonnegative().default(0),
});

export type Position = z.infer<typeof positionSchema>;
export type Size = z.infer<typeof sizeSchema>;
export type Font = z.infer<typeof fontSchema>;
export type TextRun = z.infer<typeof textRunSchema>;
export type Theme = z.infer<typeof themeSchema>;
export type Slide = z.infer<typeof slideSchema>;
export type Presentation = z.infer<typeof presentationSchema>;

export function parsePresentation(input: unknown): Presentation {
  return presentationSchema.parse(input);
}
