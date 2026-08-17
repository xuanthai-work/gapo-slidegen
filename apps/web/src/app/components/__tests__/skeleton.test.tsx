import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Skeleton } from "../skeleton";

describe("Skeleton", () => {
  it("renders a div with shimmer utility class", () => {
    const { container } = render(<Skeleton width="200px" height="40px" />);
    const div = container.firstChild as HTMLElement;
    expect(div.tagName).toBe("DIV");
    expect(div.className).toContain("u-shimmer");
  });

  it("applies inline width and height as CSS variables", () => {
    const { container } = render(<Skeleton width="320px" height="16px" />);
    const div = container.firstChild as HTMLElement;
    expect(div.style.getPropertyValue("--skeleton-width")).toBe("320px");
    expect(div.style.getPropertyValue("--skeleton-height")).toBe("16px");
  });

  it("uses default radius token when no radius prop given", () => {
    const { container } = render(<Skeleton />);
    const div = container.firstChild as HTMLElement;
    expect(div.style.getPropertyValue("--skeleton-radius")).toBe("var(--radius-sm)");
  });
});
