import PptxGenJS from "pptxgenjs";
import {
  EDITOR_STAGE_HEIGHT,
  EDITOR_STAGE_WIDTH,
  parsePresentation,
  type ChartElement,
  type Font,
  type Presentation,
  type SlideElement,
  type TextRun,
} from "@gapo-slidegen/slide-schema";

const POINTS_PER_PIXEL = 0.75;
const INCHES_PER_PIXEL = 1 / 96;
const LAYOUT_NAME = "GAPO_WIDE";

export type ResolvedAsset = { data: string } | { path: string };
export type AssetResolver = (
  assetId: string,
) => ResolvedAsset | null | Promise<ResolvedAsset | null>;

export type ExportWarning = {
  code:
    | "asset-missing"
    | "image-focus-unsupported"
    | "layout-flattened"
    | "rich-table-text-flattened";
  slideId: string;
  elementId: string;
  message: string;
};

export type ExportOptions = {
  author?: string;
  company?: string;
  resolveAsset?: AssetResolver;
};

export type ExportResult = {
  buffer: Buffer;
  warnings: ExportWarning[];
};

type Offset = { x: number; y: number };
type PptxInstance = InstanceType<typeof PptxGenJS>;
type PptxSlide = ReturnType<PptxInstance["addSlide"]>;

function color(value: string): string {
  const normalized = value.trim().replace(/^#/, "");
  if (/^[0-9a-f]{3}$/i.test(normalized)) {
    return normalized
      .split("")
      .map((character) => `${character}${character}`)
      .join("")
      .toUpperCase();
  }
  return normalized.toUpperCase();
}

function inches(value: number): number {
  return value * INCHES_PER_PIXEL;
}

function transparency(opacity = 1): number {
  return Math.round((1 - opacity) * 100);
}

function fontOptions(font: Font | undefined) {
  return {
    ...(font?.family ? { fontFace: font.family } : {}),
    ...(font?.size !== undefined ? { fontSize: font.size * POINTS_PER_PIXEL } : {}),
    ...(font?.color ? { color: color(font.color) } : {}),
    ...(font?.bold !== undefined ? { bold: font.bold } : {}),
    ...(font?.italic !== undefined ? { italic: font.italic } : {}),
    ...(font?.underline !== undefined
      ? { underline: { style: font.underline ? ("sng" as const) : ("none" as const) } }
      : {}),
    ...(font?.letterSpacing !== undefined
      ? { charSpacing: font.letterSpacing * POINTS_PER_PIXEL }
      : {}),
  };
}

function textRuns(runs: TextRun[], baseFont?: Font) {
  return runs.map((run) => ({
    text: run.text,
    options: fontOptions({ ...baseFont, ...run.font }),
  }));
}

function position(element: SlideElement, offset: Offset) {
  return {
    x: inches(offset.x + element.position.x),
    y: inches(offset.y + element.position.y),
    w: inches(element.size.width),
    h: inches(element.size.height),
  };
}

function lineOptions(stroke: {
  color: string;
  width: number;
  opacity: number;
  dash?: number[] | undefined;
}) {
  return {
    color: color(stroke.color),
    width: stroke.width * POINTS_PER_PIXEL,
    transparency: transparency(stroke.opacity),
    ...(stroke.dash ? { dashType: "dash" as const } : {}),
  };
}

function shapeFill(fill: { color: string; opacity: number } | undefined) {
  return fill
    ? { color: color(fill.color), transparency: transparency(fill.opacity) }
    : { color: "FFFFFF", transparency: 100 };
}

function chartType(pptx: PptxInstance, element: ChartElement) {
  switch (element.chartType) {
    case "area":
      return pptx.ChartType.area;
    case "bar":
    case "horizontal-bar":
    case "stacked-bar":
      return pptx.ChartType.bar;
    case "donut":
      return pptx.ChartType.doughnut;
    case "line":
      return pptx.ChartType.line;
    case "pie":
      return pptx.ChartType.pie;
    case "radar":
      return pptx.ChartType.radar;
    case "scatter":
      return pptx.ChartType.scatter;
  }
}

async function addElement(
  pptx: PptxInstance,
  slide: PptxSlide,
  element: SlideElement,
  slideId: string,
  warnings: ExportWarning[],
  resolveAsset: AssetResolver | undefined,
  offset: Offset = { x: 0, y: 0 },
): Promise<void> {
  const box = position(element, offset);
  const objectName = element.name ?? element.id;

  switch (element.type) {
    case "text":
      slide.addText(textRuns(element.runs, element.font), {
        ...box,
        objectName,
        rotate: element.rotation,
        margin: 0,
        breakLine: false,
        fit: "shrink",
        align: element.horizontalAlign,
        valign: element.verticalAlign,
        fill: element.fill ? shapeFill(element.fill) : { color: "FFFFFF", transparency: 100 },
        ...(element.stroke ? { line: lineOptions(element.stroke) } : {}),
      });
      return;

    case "text-list": {
      const runs = element.items.map((item, index) => ({
        text: item.map((run) => run.text).join(""),
        options: {
          ...fontOptions(element.font),
          breakLine: index < element.items.length - 1,
          ...(element.marker === "none"
            ? {}
            : { bullet: element.marker === "bullet" ? true : { type: "number" as const } }),
        },
      }));
      slide.addText(runs, {
        ...box,
        objectName,
        rotate: element.rotation,
        margin: 0,
        fit: "shrink",
      });
      return;
    }

    case "shape": {
      const shape =
        element.shape === "rectangle"
          ? element.cornerRadius > 0
            ? pptx.ShapeType.roundRect
            : pptx.ShapeType.rect
          : element.shape === "ellipse"
            ? pptx.ShapeType.ellipse
            : element.shape === "triangle"
              ? pptx.ShapeType.triangle
              : pptx.ShapeType.diamond;
      slide.addShape(shape, {
        ...box,
        objectName,
        rotate: element.rotation,
        fill: shapeFill(element.fill),
        ...(element.stroke ? { line: lineOptions(element.stroke) } : {}),
      });
      return;
    }

    case "line":
      slide.addShape(pptx.ShapeType.line, {
        ...box,
        objectName,
        rotate: element.rotation,
        line: {
          ...lineOptions(element.stroke),
          beginArrowType: element.startArrow ? "triangle" : "none",
          endArrowType: element.endArrow ? "triangle" : "none",
        },
      });
      return;

    case "image": {
      const asset = await resolveAsset?.(element.assetId);
      if (!asset) {
        warnings.push({
          code: "asset-missing",
          slideId,
          elementId: element.id,
          message: `Asset ${element.assetId} was not resolved; image omitted.`,
        });
        return;
      }
      if (element.focusX !== 0.5 || element.focusY !== 0.5 || element.cropScale !== 1) {
        warnings.push({
          code: "image-focus-unsupported",
          slideId,
          elementId: element.id,
          message: "Custom image focus and crop scale are not represented by the current PPTX adapter.",
        });
      }
      slide.addImage({
        ...asset,
        ...box,
        objectName,
        altText: element.alt,
        rotate: element.rotation,
        flipH: element.flipHorizontal,
        flipV: element.flipVertical,
        transparency: transparency(element.opacity),
        ...(element.fit === "fill"
          ? {}
          : { sizing: { type: element.fit, w: box.w, h: box.h } }),
      });
      return;
    }

    case "table": {
      const rows = element.rows.map((row) =>
        row.map((cell) => {
          if (cell.runs.length > 1 || cell.runs.some((run) => run.font)) {
            warnings.push({
              code: "rich-table-text-flattened",
              slideId,
              elementId: element.id,
              message: "Per-run table cell formatting was flattened to cell formatting.",
            });
          }
          return {
            text: cell.runs.map((run) => run.text).join(""),
            options: {
              ...fontOptions(cell.font),
              align: cell.horizontalAlign,
              ...(cell.fill ? { fill: shapeFill(cell.fill) } : {}),
            },
          };
        }),
      );
      slide.addTable(rows, {
        ...box,
        objectName,
        margin: 2,
        border: { color: "D6DCE5", pt: 1 },
        ...(element.columnWidths
          ? { colW: element.columnWidths.map(inches) }
          : {}),
        ...(element.rowHeights ? { rowH: element.rowHeights.map(inches) } : {}),
      });
      return;
    }

    case "chart":
      slide.addChart(
        chartType(pptx, element),
        element.series.map((series) => ({
          name: series.name,
          labels: element.categories,
          values: series.values,
        })),
        {
          ...box,
          objectName,
          showLegend: element.showLegend,
          showTitle: false,
          showValue: false,
          catAxisLabelFontFace: "Arial",
          valAxisLabelFontFace: "Arial",
          ...(element.chartType === "horizontal-bar" ? { barDir: "bar" as const } : {}),
          ...(element.chartType === "stacked-bar"
            ? { grouping: "stacked" as const, barDir: "col" as const }
            : {}),
          ...(element.colors ? { chartColors: element.colors.map(color) } : {}),
        },
      );
      return;

    case "svg": {
      const data = `data:image/svg+xml;base64,${Buffer.from(element.svg).toString("base64")}`;
      slide.addImage({ data, ...box, objectName, altText: element.alt, rotate: element.rotation });
      return;
    }

    case "container": {
      slide.addShape(pptx.ShapeType.rect, {
        ...box,
        objectName,
        rotate: element.rotation,
        fill: shapeFill(element.fill),
        ...(element.stroke ? { line: lineOptions(element.stroke) } : {}),
      });
      if (element.child) {
        await addElement(
          pptx,
          slide,
          element.child,
          slideId,
          warnings,
          resolveAsset,
          { x: offset.x + element.position.x, y: offset.y + element.position.y },
        );
      }
      return;
    }

    case "group":
    case "flex":
    case "grid": {
      warnings.push({
        code: "layout-flattened",
        slideId,
        elementId: element.id,
        message: `${element.type} was exported as individually editable child objects.`,
      });
      const childOffset = {
        x: offset.x + element.position.x,
        y: offset.y + element.position.y,
      };
      for (const child of element.children) {
        await addElement(pptx, slide, child, slideId, warnings, resolveAsset, childOffset);
      }
      return;
    }
  }
}

export async function exportPresentationToPptx(
  input: Presentation | unknown,
  options: ExportOptions = {},
): Promise<ExportResult> {
  const presentation = parsePresentation(input);
  const pptx = new PptxGenJS();
  const warnings: ExportWarning[] = [];

  pptx.defineLayout({
    name: LAYOUT_NAME,
    width: inches(EDITOR_STAGE_WIDTH),
    height: inches(EDITOR_STAGE_HEIGHT),
  });
  pptx.layout = LAYOUT_NAME;
  pptx.author = options.author ?? "Gapo Slidegen";
  pptx.company = options.company ?? "Gapo";
  pptx.subject = presentation.title;
  pptx.title = presentation.title;
  pptx.theme = {
    headFontFace: presentation.theme.fonts.heading,
    bodyFontFace: presentation.theme.fonts.body,
  };

  for (const sourceSlide of presentation.slides) {
    const slide = pptx.addSlide();
    slide.background = { color: color(sourceSlide.background) };
    for (const element of sourceSlide.elements) {
      await addElement(
        pptx,
        slide,
        element,
        sourceSlide.id,
        warnings,
        options.resolveAsset,
      );
    }
  }

  const output = await pptx.write({ outputType: "nodebuffer", compression: true });
  return {
    buffer: Buffer.isBuffer(output) ? output : Buffer.from(output as ArrayBuffer),
    warnings,
  };
}
