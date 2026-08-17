import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CommandPalette } from "../command-palette";

const commands = [
  {
    id: "new",
    label: "New presentation",
    shortcut: "Ctrl+N",
    section: "File",
    action: vi.fn(),
  },
  {
    id: "open",
    label: "Open presentation",
    section: "File",
    action: vi.fn(),
  },
  {
    id: "save",
    label: "Save",
    shortcut: "Ctrl+S",
    section: "File",
    action: vi.fn(),
  },
  {
    id: "undo",
    label: "Undo",
    section: "Edit",
    action: vi.fn(),
  },
  {
    id: "find",
    label: "Find",
    section: "Edit",
    action: vi.fn(),
  },
];

function renderPalette(props = {}) {
  const onClose = vi.fn();
  const result = render(
    <CommandPalette
      isOpen={true}
      onClose={onClose}
      commands={commands.map((command) => ({ ...command, action: vi.fn() }))}
      {...props}
    />,
  );
  return { ...result, onClose };
}

describe("CommandPalette", () => {
  it("renders grouped list of commands", () => {
    renderPalette();

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Search commands…")).toBeInTheDocument();

    expect(screen.getByText("File")).toBeInTheDocument();
    expect(screen.getByText("Edit")).toBeInTheDocument();

    expect(screen.getByText("New presentation")).toBeInTheDocument();
    expect(screen.getByText("Open presentation")).toBeInTheDocument();
    expect(screen.getByText("Save")).toBeInTheDocument();
    expect(screen.getByText("Undo")).toBeInTheDocument();
    expect(screen.getByText("Find")).toBeInTheDocument();
  });

  it("filters commands when typing", () => {
    renderPalette();

    const input = screen.getByPlaceholderText("Search commands…");
    fireEvent.input(input, { target: { value: "open" } });

    expect(screen.getByText("Open presentation")).toBeInTheDocument();
    expect(screen.queryByText("New presentation")).not.toBeInTheDocument();
    expect(screen.queryByText("Save")).not.toBeInTheDocument();
  });

  it("navigates with arrow keys and runs the highlighted action on Enter", () => {
    const actionMocks = commands.map((command) => ({ ...command, action: vi.fn() }));
    render(
      <CommandPalette isOpen={true} onClose={vi.fn()} commands={actionMocks} />,
    );

    const input = screen.getByPlaceholderText("Search commands…");

    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(actionMocks[2]!.action).toHaveBeenCalledTimes(1);
  });

  it("closes when Escape is pressed", () => {
    const { onClose } = renderPalette();

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes when the backdrop is clicked", () => {
    const { container, onClose } = renderPalette();

    const backdrop = container.querySelector(".command-palette-backdrop");
    expect(backdrop).not.toBeNull();
    fireEvent.click(backdrop!);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows an empty state when the filter matches nothing", () => {
    renderPalette();

    const input = screen.getByPlaceholderText("Search commands…");
    fireEvent.input(input, { target: { value: "zzzzz" } });

    expect(screen.getByText("No commands match your search.")).toBeInTheDocument();
    expect(screen.queryByText("New presentation")).not.toBeInTheDocument();
  });
});
