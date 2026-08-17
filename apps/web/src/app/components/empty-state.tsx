"use client";

import type { ReactNode } from "react";

export interface EmptyStateProps {
  icon?: ReactNode;
  eyebrow?: string;
  heading: string;
  body?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({
  icon,
  eyebrow,
  heading,
  body,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="empty-state">
      {icon ? <div className="empty-state__icon">{icon}</div> : null}
      {eyebrow ? <p className="empty-state__eyebrow">{eyebrow}</p> : null}
      <h3 className="empty-state__heading">{heading}</h3>
      {body ? <p className="empty-state__body">{body}</p> : null}
      {actionLabel && onAction ? (
        <button type="button" className="empty-state__action u-focus-ring" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
