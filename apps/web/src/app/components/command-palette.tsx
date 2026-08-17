"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode, KeyboardEvent } from "react";

export type CommandAction = {
  id: string;
  label: string;
  shortcut?: string;
  section: string;
  icon?: ReactNode;
  action: () => void;
};

export type CommandPaletteProps = {
  isOpen: boolean;
  onClose: () => void;
  commands: CommandAction[];
};

export function CommandPalette({ isOpen, onClose, commands }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [highlightIndex, setHighlightIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const filtered = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return commands;
    return commands.filter(
      (command) =>
        command.label.toLowerCase().includes(trimmed) ||
        command.section.toLowerCase().includes(trimmed),
    );
  }, [commands, query]);

  const grouped = useMemo(() => {
    const map = new Map<string, CommandAction[]>();
    for (const command of filtered) {
      const list = map.get(command.section) ?? [];
      list.push(command);
      map.set(command.section, list);
    }
    return Array.from(map.entries()).map(([section, items]) => ({ section, items }));
  }, [filtered]);

  const flat = useMemo(() => grouped.flatMap((group) => group.items), [grouped]);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setHighlightIndex(commands.length > 0 ? 0 : -1);
      inputRef.current?.focus();
    }
  }, [isOpen, commands.length]);

  useEffect(() => {
    setHighlightIndex(flat.length > 0 ? 0 : -1);
  }, [flat.length]);

  useEffect(() => {
    const el = itemRefs.current[highlightIndex];
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ block: "nearest" });
    }
  }, [highlightIndex]);

  if (!isOpen) {
    return null;
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }

    if (flat.length === 0) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlightIndex((index) => (index + 1) % flat.length);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlightIndex((index) => (index - 1 + flat.length) % flat.length);
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      const command = flat[highlightIndex];
      if (command) {
        command.action();
      }
    }
  }

  let globalIndex = 0;

  return (
    <div className="command-palette-backdrop" onClick={onClose}>
      <div
        className="command-palette"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <input
          ref={inputRef}
          type="text"
          className="command-palette__input u-focus-ring"
          placeholder="Search commands…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label="Search commands"
        />
        {flat.length === 0 ? (
          <div className="command-palette__empty">No commands match your search.</div>
        ) : (
          <div className="command-palette__groups" role="listbox">
            {grouped.map(({ section, items }) => (
              <div key={section} className="command-palette__group" role="group" aria-label={section}>
                <div className="command-palette__group-title">{section}</div>
                {items.map((command) => {
                  const index = globalIndex++;
                  const isHighlighted = index === highlightIndex;
                  return (
                    <button
                      key={command.id}
                      ref={(el) => {
                        itemRefs.current[index] = el;
                      }}
                      type="button"
                      className={`command-palette__item ${
                        isHighlighted ? "command-palette__item--highlighted" : ""
                      } u-focus-ring`}
                      role="option"
                      aria-selected={isHighlighted}
                      onClick={() => command.action()}
                    >
                      <span className="command-palette__item-main">
                        {command.icon && (
                          <span className="command-palette__item-icon" aria-hidden="true">
                            {command.icon}
                          </span>
                        )}
                        <span>{command.label}</span>
                      </span>
                      {command.shortcut && (
                        <kbd className="command-palette__shortcut">{command.shortcut}</kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
