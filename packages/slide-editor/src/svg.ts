export const DEFAULT_SVG_COLOR = "#1E4CD9";

export function prepareSvgMarkup(svg: string, color = DEFAULT_SVG_COLOR): string {
  return svg.replace(/currentColor/g, color);
}

export function svgDataUrl(svg: string, color = DEFAULT_SVG_COLOR): string {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(prepareSvgMarkup(svg, color))}`;
}
