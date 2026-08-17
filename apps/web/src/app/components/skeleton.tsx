import type { CSSProperties } from "react";

export interface SkeletonProps {
  width?: string;
  height?: string;
  radius?: string;
  className?: string;
}

export function Skeleton({
  width = "100%",
  height = "1em",
  radius = "var(--radius-sm)",
  className = "",
}: SkeletonProps) {
  const style: CSSProperties = {
    "--skeleton-width": width,
    "--skeleton-height": height,
    "--skeleton-radius": radius,
    width: "var(--skeleton-width)",
    height: "var(--skeleton-height)",
    borderRadius: "var(--skeleton-radius)",
    display: "block",
  };
  return <div className={`u-shimmer ${className}`.trim()} style={style} aria-hidden="true" />;
}
