import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState } from "../empty-state";

describe("EmptyState", () => {
  it("renders eyebrow, heading, and body when provided", () => {
    render(
      <EmptyState
        eyebrow="Your decks"
        heading="No presentations yet"
        body="Generated presentations will appear here."
      />,
    );
    expect(screen.getByText("Your decks")).toBeInTheDocument();
    expect(screen.getByText("No presentations yet")).toBeInTheDocument();
    expect(screen.getByText("Generated presentations will appear here.")).toBeInTheDocument();
  });

  it("renders action label as a button when provided", () => {
    render(
      <EmptyState
        heading="Empty"
        actionLabel="Create your first deck"
        onAction={() => {}}
      />,
    );
    const button = screen.getByRole("button", { name: "Create your first deck" });
    expect(button).toBeInTheDocument();
  });

  it("does not render action button when no actionLabel", () => {
    render(<EmptyState heading="Empty" />);
    expect(screen.queryByRole("button")).toBeNull();
  });
});
