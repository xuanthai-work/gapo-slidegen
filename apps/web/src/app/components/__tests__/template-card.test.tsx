import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TemplateCard } from "../template-card";

const palette = {
  paper: "#FFFFFF",
  ink: "#161618",
  accent: "#B8651E",
};

describe("TemplateCard", () => {
  it("renders the theme name", () => {
    render(
      <TemplateCard
        id="modern-blue"
        name="Modern Blue"
        colors={palette}
        selected={false}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("Modern Blue")).toBeInTheDocument();
  });

  it("applies is-selected class when selected is true", () => {
    const { container } = render(
      <TemplateCard
        id="modern-blue"
        name="Modern Blue"
        colors={palette}
        selected={true}
        onSelect={() => {}}
      />,
    );
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain("is-selected");
  });

  it("calls onSelect with the theme id when clicked", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <TemplateCard
        id="warm-studio"
        name="Warm Studio"
        colors={palette}
        selected={false}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(container.firstChild as HTMLElement);
    expect(onSelect).toHaveBeenCalledWith("warm-studio");
  });

  it("sets role=radio and aria-checked for radio-group semantics", () => {
    render(
      <TemplateCard
        id="modern-blue"
        name="Modern Blue"
        colors={palette}
        selected={true}
        onSelect={() => {}}
      />,
    );
    const card = screen.getByRole("radio", { name: /Modern Blue/i });
    expect(card.getAttribute("aria-checked")).toBe("true");
  });
});
