import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./styles.css";

const themeInitScript = `
try {
  var stored = localStorage.getItem("theme");
  var prefers = window.matchMedia("(prefers-color-scheme: dark)").matches;
  if (stored === "dark" || (!stored && prefers)) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
} catch (e) {}
`;

export const metadata: Metadata = {
  title: "Gapo SlideGen",
  description: "Create and edit presentations with AI assistance.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  const defaultLang =
    typeof navigator !== "undefined" && navigator.language?.toLowerCase().startsWith("vi")
      ? "vi"
      : "en";

  return (
    <html lang={defaultLang} suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
