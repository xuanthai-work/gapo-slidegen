import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemeHud } from "../theme-hud";

describe("ThemeHud", () => {
  it("does not render when closed", () => {
    render(
      <ThemeHud open={false} onCancel={() => {}} onConfirm={() => {}} />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("starts on the layout pack step with Modern selected", () => {
    render(
      <ThemeHud open={true} onCancel={() => {}} onConfirm={() => {}} />,
    );
    expect(screen.getByRole("dialog", { name: /visual system/i })).toBeInTheDocument();
    expect(screen.getByText(/select layout pack/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Use Modern" })).toBeInTheDocument();
  });

  it("advances to color schemes then confirms the default pair", () => {
    const onConfirm = vi.fn();
    render(
      <ThemeHud open={true} onCancel={() => {}} onConfirm={onConfirm} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Use Modern" }));
    expect(screen.getByText(/select color scheme/i)).toBeInTheDocument();
    expect(screen.getByText(/Modern with Professional Blue/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate presentation" }));
    expect(onConfirm).toHaveBeenCalledWith({
      templateId: "modern",
      colorSchemeId: "professional-blue",
    });
  });

  it("closes without confirming on Escape or backdrop", () => {
    const onCancel = vi.fn();
    render(
      <ThemeHud open={true} onCancel={onCancel} onConfirm={() => {}} />,
    );
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onCancel).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Close theme picker" }));
    expect(onCancel).toHaveBeenCalledTimes(2);
  });
});
