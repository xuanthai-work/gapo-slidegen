import { describe, expect, it } from "vitest";
import { prepareSvgMarkup, svgDataUrl } from "../src/svg";

describe("svg helpers", () => {
  it("replaces currentColor before encoding", () => {
    const url = svgDataUrl('<svg stroke="currentColor"></svg>', "#112233");
    expect(url).toContain(encodeURIComponent("#112233"));
    expect(url).not.toContain("currentColor");
  });

  it("prepares markup without changing explicit colors", () => {
    expect(prepareSvgMarkup('<svg stroke="#445566"></svg>')).toBe('<svg stroke="#445566"></svg>');
  });
});
