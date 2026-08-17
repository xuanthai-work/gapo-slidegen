import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "../toast-provider";
import { useToast } from "../use-toast";

function TestButton({
  type,
  message,
  duration,
}: {
  type: "success" | "error" | "info";
  message: string;
  duration?: number;
}) {
  const { toast } = useToast();
  return (
    <button type="button" onClick={() => toast(type, message, duration)}>
      Show toast
    </button>
  );
}

describe("Toast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows an error toast message", () => {
    render(
      <ToastProvider>
        <TestButton type="error" message="Something went wrong" />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /show toast/i }));

    expect(screen.getByRole("status")).toHaveTextContent("Something went wrong");
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("auto-dismisses after the duration", () => {
    render(
      <ToastProvider>
        <TestButton type="info" message="Auto dismiss" duration={1000} />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /show toast/i }));
    expect(screen.getByRole("status")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1000 + 220);
    });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("pauses dismissal while hovering", () => {
    render(
      <ToastProvider>
        <TestButton type="success" message="Hover me" duration={1000} />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /show toast/i }));
    const toast = screen.getByRole("status");

    fireEvent.mouseEnter(toast);
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(screen.getByRole("status")).toBeInTheDocument();

    fireEvent.mouseLeave(toast);
    act(() => {
      vi.advanceTimersByTime(1000 + 220);
    });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("removes toast when dismiss button is clicked", () => {
    render(
      <ToastProvider>
        <TestButton type="info" message="Dismiss me" />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /show toast/i }));
    const dismissButton = screen.getByRole("button", { name: /dismiss notification/i });

    fireEvent.click(dismissButton);
    act(() => {
      vi.advanceTimersByTime(220);
    });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
