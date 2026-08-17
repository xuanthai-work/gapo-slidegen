"use client";

import { Check, Info, XCircle } from "@phosphor-icons/react";
import { memo } from "react";
import type { Toast, ToastType } from "./use-toast";

const DEFAULT_DURATION = 5000;

const ICONS: Record<ToastType, typeof Check> = {
  success: Check,
  error: XCircle,
  info: Info,
};

type ToastItemProps = {
  toast: Toast;
  onDismiss: () => void;
  onHoverStart: () => void;
  onHoverEnd: () => void;
  exiting?: boolean;
};

export const ToastItem = memo(function ToastItem({
  toast,
  onDismiss,
  onHoverStart,
  onHoverEnd,
  exiting,
}: ToastItemProps) {
  const Icon = ICONS[toast.type];
  const duration = toast.duration ?? DEFAULT_DURATION;

  return (
    <div
      className={["toast-item", exiting && "toast-item--exiting"].filter(Boolean).join(" ")}
      role="status"
      aria-live="polite"
      onMouseEnter={onHoverStart}
      onMouseLeave={onHoverEnd}
    >
      <div className="toast-row">
        <span className={`toast-icon toast-icon--${toast.type}`} aria-hidden="true">
          <Icon size={18} weight="bold" />
        </span>
        <p className="toast-message">{toast.message}</p>
        <button
          type="button"
          className="toast-close u-focus-ring"
          aria-label="Dismiss notification"
          onClick={onDismiss}
        >
          <span aria-hidden="true">×</span>
        </button>
      </div>
      <span
        className={`toast-progress toast-progress--${toast.type}`}
        style={{ animationDuration: `${duration}ms` }}
      />
    </div>
  );
});
