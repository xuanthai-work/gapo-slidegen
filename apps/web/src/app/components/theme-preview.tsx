export interface ThemePreviewColors {
  paper: string;
  ink: string;
  accent: string;
}

export interface ThemePreviewProps {
  colors: ThemePreviewColors;
  name: string;
}

export function ThemePreview({ colors, name }: ThemePreviewProps) {
  return (
    <div
      className="theme-preview"
      role="img"
      aria-label={`${name} theme preview`}
      style={{
        background: colors.paper,
        color: colors.ink,
      }}
    >
      <div className="theme-preview__band" style={{ background: colors.accent }} />
      <div className="theme-preview__heading" style={{ background: colors.ink, opacity: 0.85 }} />
      <div className="theme-preview__line theme-preview__line--long" style={{ background: colors.ink, opacity: 0.35 }} />
      <div className="theme-preview__line theme-preview__line--short" style={{ background: colors.ink, opacity: 0.35 }} />
      <div className="theme-preview__row">
        <span style={{ background: colors.accent, opacity: 0.6 }} />
        <span style={{ background: colors.ink, opacity: 0.20 }} />
        <span style={{ background: colors.ink, opacity: 0.20 }} />
      </div>
    </div>
  );
}
