"use client";

import { CaretLeft, CaretRight, X } from "@phosphor-icons/react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import {
  DEFAULT_COLOR_SCHEME_ID,
  DEFAULT_TEMPLATE_ID,
  PRESENTON_COLOR_SCHEMES,
  PRESENTON_TEMPLATES,
  type ColorSchemeId,
  type ColorSchemeOption,
  type TemplateId,
  type TemplateOption,
} from "../../lib/presenton-catalog";

export type ThemeHudSelection = {
  templateId: TemplateId;
  colorSchemeId: ColorSchemeId;
};

type ThemeHudProps = {
  open: boolean;
  submitting?: boolean;
  onCancel: () => void;
  onConfirm: (selection: ThemeHudSelection) => void;
};

type HudStep = "layout" | "color";

function isColorScheme(item: TemplateOption | ColorSchemeOption): item is ColorSchemeOption {
  return "paper" in item;
}

export function ThemeHud({ open, submitting = false, onCancel, onConfirm }: ThemeHudProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [step, setStep] = useState<HudStep>("layout");
  const [templateIndex, setTemplateIndex] = useState(0);
  const [schemeIndex, setSchemeIndex] = useState(0);

  const template = PRESENTON_TEMPLATES[templateIndex] ?? PRESENTON_TEMPLATES[0]!;
  const scheme = PRESENTON_COLOR_SCHEMES[schemeIndex] ?? PRESENTON_COLOR_SCHEMES[0]!;
  const items = step === "layout" ? PRESENTON_TEMPLATES : PRESENTON_COLOR_SCHEMES;
  const focused = step === "layout" ? templateIndex : schemeIndex;

  useEffect(() => {
    if (!open) {
      setStep("layout");
      setTemplateIndex(PRESENTON_TEMPLATES.findIndex((item) => item.id === DEFAULT_TEMPLATE_ID));
      setSchemeIndex(PRESENTON_COLOR_SCHEMES.findIndex((item) => item.id === DEFAULT_COLOR_SCHEME_ID));
      document.body.classList.remove("theme-hud-open");
      return;
    }
    document.body.classList.add("theme-hud-open");
    rootRef.current?.focus();
    return () => document.body.classList.remove("theme-hud-open");
  }, [open]);

  if (!open) return null;

  function move(delta: number) {
    if (step === "layout") {
      setTemplateIndex((current) => (current + delta + PRESENTON_TEMPLATES.length) % PRESENTON_TEMPLATES.length);
      return;
    }
    setSchemeIndex((current) => (current + delta + PRESENTON_COLOR_SCHEMES.length) % PRESENTON_COLOR_SCHEMES.length);
  }

  function confirm() {
    onConfirm({ templateId: template.id, colorSchemeId: scheme.id });
  }

  function handleKey(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      onCancel();
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      move(1);
      return;
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      move(-1);
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      if (step === "layout") setStep("color");
      else if (!submitting) confirm();
    }
  }

  return (
    <div
      ref={rootRef}
      className="theme-hud"
      role="dialog"
      aria-modal="true"
      aria-labelledby="theme-hud-title"
      tabIndex={-1}
      onKeyDown={handleKey}
    >
      <button className="theme-hud__backdrop" type="button" aria-label="Close theme picker" onClick={onCancel} />
      <div className="theme-hud__frame">
        <header className="theme-hud__top">
          <p className="theme-hud__kicker">
            {step === "layout" ? "01  Select layout pack" : "02  Select color scheme"}
          </p>
          <h2 id="theme-hud-title">Visual system</h2>
          <button className="icon-button theme-hud__close" type="button" aria-label="Close" onClick={onCancel}>
            <X size={16} />
          </button>
        </header>

        <div className="theme-hud__stage">
          <button className="theme-hud__nav" type="button" aria-label="Previous" onClick={() => move(-1)}>
            <CaretLeft size={22} />
          </button>
          <div className="theme-hud__rail" aria-live="polite">
            {items.map((item, index) => {
              const offset = index - focused;
              const selected = index === focused;
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`theme-hud__card${selected ? " is-focused" : ""}`}
                  style={{
                    transform: `translate(-50%, -50%) translateX(${offset * 220}px) scale(${selected ? 1 : 0.78}) rotateY(${offset * 16}deg)`,
                    zIndex: 20 - Math.abs(offset),
                    opacity: Math.abs(offset) > 2 ? 0 : selected ? 1 : 0.45,
                    pointerEvents: Math.abs(offset) > 2 ? "none" : "auto",
                  }}
                  aria-pressed={selected}
                  onClick={() => {
                    if (step === "layout") setTemplateIndex(index);
                    else setSchemeIndex(index);
                  }}
                >
                  {isColorScheme(item) ? (
                    <span
                      className="theme-hud__swatch"
                      style={{
                        background: item.paper,
                        color: item.ink,
                        boxShadow: `inset 0 -18px 0 ${item.accent}`,
                      }}
                    />
                  ) : (
                    <span className={`theme-hud__preview theme-hud__preview--${item.id}`} />
                  )}
                  <strong>{item.name}</strong>
                </button>
              );
            })}
          </div>
          <button className="theme-hud__nav" type="button" aria-label="Next" onClick={() => move(1)}>
            <CaretRight size={22} />
          </button>
        </div>

        <p className="theme-hud__caption">
          {step === "layout" ? template.pitch : `${template.name} with ${scheme.name}`}
        </p>

        <footer className="theme-hud__actions">
          {step === "color" ? (
            <button className="button" type="button" onClick={() => setStep("layout")}>
              Back
            </button>
          ) : (
            <span />
          )}
          {step === "layout" ? (
            <button className="button button--primary" type="button" onClick={() => setStep("color")}>
              Use {template.name}
            </button>
          ) : (
            <button
              className="button button--primary"
              type="button"
              disabled={submitting}
              onClick={confirm}
            >
              {submitting ? "Working…" : "Generate presentation"}
            </button>
          )}
        </footer>
      </div>
    </div>
  );
}
