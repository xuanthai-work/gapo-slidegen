"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { CommandPalette } from "./command-palette";
import type { CommandAction } from "./command-palette";

export type CommandPaletteTriggerProps = {
  commands: CommandAction[];
  children?: ReactNode;
};

export function CommandPaletteTrigger({ commands, children }: CommandPaletteTriggerProps) {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && isOpen) {
        event.preventDefault();
        setIsOpen(false);
        return;
      }

      const isCommandK = (event.metaKey || event.ctrlKey) && event.key === "k";
      if (!isCommandK) return;

      const target = event.target as HTMLElement | null;
      if (!target) return;

      const tag = target.tagName?.toLowerCase();
      if (
        tag === "input" ||
        tag === "textarea" ||
        tag === "select" ||
        target.isContentEditable
      ) {
        return;
      }

      event.preventDefault();
      setIsOpen(true);
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  return (
    <>
      {children}
      <CommandPalette
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        commands={commands}
      />
    </>
  );
}
