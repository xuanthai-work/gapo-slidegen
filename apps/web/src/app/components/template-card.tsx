"use client";

import { Check } from "@phosphor-icons/react";
import type { KeyboardEvent } from "react";
import { ThemePreview, type ThemePreviewColors } from "./theme-preview";

export interface TemplateCardProps {
  id: string;
  name: string;
  colors: ThemePreviewColors;
  selected: boolean;
  onSelect: (id: string) => void;
}

export function TemplateCard({ id, name, colors, selected, onSelect }: TemplateCardProps) {
  function handleKey(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(id);
    }
  }

  return (
    <div
      className={`template-card u-lift u-focus-ring${selected ? " is-selected" : ""}`}
      role="radio"
      aria-checked={selected}
      tabIndex={0}
      onClick={() => onSelect(id)}
      onKeyDown={handleKey}
    >
      <ThemePreview colors={colors} name={name} />
      <div className="template-card__footer">
        <span className="template-card__name">{name}</span>
        {selected ? (
          <span className="template-card__check" aria-hidden="true">
            <Check size={14} weight="bold" />
          </span>
        ) : null}
      </div>
    </div>
  );
}
