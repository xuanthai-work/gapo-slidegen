import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { canonicalPresentationFixture } from "@gapo-slidegen/slide-schema/fixtures";
import type { Slide, SlideElement } from "@gapo-slidegen/slide-schema";
import { SlideThumbnail } from "../slide-thumbnail";

function makeSlide(elements: SlideElement[]): Slide {
  return {
    id: "test-slide",
    title: "Test slide",
    background: "#FFFFFF",
    revision: 0,
    elements,
  };
}

describe("SlideThumbnail", () => {
  it("renders the slide text content", () => {
    render(
      <SlideThumbnail slide={canonicalPresentationFixture.slides[0]!} />,
    );
    expect(screen.getByText("Quarterly product review")).toBeInTheDocument();
  });

  it("renders a shape with its fill color", () => {
    const slide = makeSlide([
      {
        id: "shape",
        type: "shape",
        shape: "rectangle",
        position: { x: 0, y: 0 },
        size: { width: 640, height: 360 },
        rotation: 0,
        opacity: 1,
        locked: false,
        decorative: true,
        fill: { color: "#285FC7", opacity: 1 },
        cornerRadius: 0,
      },
    ]);
    const { container } = render(<SlideThumbnail slide={slide} />);
    const shape = container.querySelector(".slide-thumbnail > div");
    expect(shape).toHaveStyle({ backgroundColor: "#285FC7" });
  });

  it("renders an image when resolveAssetUrl is provided", () => {
    const slide = makeSlide([
      {
        id: "image",
        type: "image",
        position: { x: 0, y: 0 },
        size: { width: 640, height: 360 },
        rotation: 0,
        opacity: 1,
        locked: false,
        decorative: true,
        assetId: "asset-123",
        fit: "cover",
        focusX: 0.5,
        focusY: 0.5,
        cropScale: 1,
        flipHorizontal: false,
        flipVertical: false,
        alt: "Hero",
      },
    ]);
    render(
      <SlideThumbnail
        slide={slide}
        resolveAssetUrl={(id) => `https://cdn.example/${id}`}
      />,
    );
    expect(screen.getByAltText("Hero")).toHaveAttribute(
      "src",
      "https://cdn.example/asset-123",
    );
  });

  it("renders an inline svg element", () => {
    const slide = makeSlide([
      {
        id: "icon",
        type: "svg",
        position: { x: 0, y: 0 },
        size: { width: 120, height: 120 },
        rotation: 0,
        opacity: 1,
        locked: false,
        decorative: true,
        svg: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><circle cx="128" cy="128" r="96" fill="none" stroke="currentColor" stroke-width="16"/></svg>',
        alt: "Workflow icon",
      },
    ]);
    render(<SlideThumbnail slide={slide} />);
    const icon = screen.getByAltText("Workflow icon");
    expect(icon).toHaveAttribute("src", expect.stringContaining("data:image/svg+xml"));
  });

  it("falls back to a placeholder when resolveAssetUrl is missing", () => {
    const slide = makeSlide([
      {
        id: "image",
        type: "image",
        position: { x: 0, y: 0 },
        size: { width: 640, height: 360 },
        rotation: 0,
        opacity: 1,
        locked: false,
        decorative: true,
        assetId: "asset-123",
        fit: "cover",
        focusX: 0.5,
        focusY: 0.5,
        cropScale: 1,
        flipHorizontal: false,
        flipVertical: false,
        alt: "Hero",
      },
    ]);
    const { container } = render(<SlideThumbnail slide={slide} />);
    expect(container.querySelector("img")).not.toBeInTheDocument();
    expect(container.querySelector(".slide-thumbnail > div")).toBeInTheDocument();
  });

  it("flattens group children into the thumbnail", () => {
    const slide = makeSlide([
      {
        id: "group",
        type: "group",
        position: { x: 0, y: 0 },
        size: { width: 1280, height: 720 },
        rotation: 0,
        opacity: 1,
        locked: false,
        decorative: true,
        children: [
          {
            id: "grouped-text",
            type: "text",
            position: { x: 96, y: 104 },
            size: { width: 760, height: 180 },
            rotation: 0,
            opacity: 1,
            locked: false,
            decorative: false,
            runs: [{ text: "Grouped text" }],
            horizontalAlign: "left",
            verticalAlign: "top",
          },
        ],
      },
    ]);
    render(<SlideThumbnail slide={slide} />);
    expect(screen.getByText("Grouped text")).toBeInTheDocument();
  });

  it("ignores unsupported element types without crashing", () => {
    const slide = makeSlide([
      {
        id: "line",
        type: "line",
        position: { x: 0, y: 0 },
        size: { width: 100, height: 100 },
        rotation: 0,
        opacity: 1,
        locked: false,
        decorative: true,
        stroke: { color: "#000", width: 2, opacity: 1 },
        startArrow: false,
        endArrow: false,
      },
    ]);
    const { container } = render(<SlideThumbnail slide={slide} />);
    expect(container.querySelector(".slide-thumbnail")).toBeInTheDocument();
  });
});
