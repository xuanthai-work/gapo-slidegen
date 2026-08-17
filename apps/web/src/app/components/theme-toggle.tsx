"use client";

import { Moon, Sun } from "@phosphor-icons/react";
import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function readTheme(): Theme {
  if (typeof document === "undefined") return "light";
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setTheme(readTheme());
  }, []);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    if (next === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    try {
      localStorage.setItem("theme", next);
    } catch {}
  }

  return (
    <button
      type="button"
      className="theme-toggle u-focus-ring"
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      aria-pressed={theme === "dark"}
      onClick={toggle}
    >
      {mounted ? (theme === "dark" ? <Sun size={17} /> : <Moon size={17} />) : <Moon size={17} />}
    </button>
  );
}
