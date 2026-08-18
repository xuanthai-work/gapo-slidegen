import { useState } from "react";
import { svgDataUrl } from "@gapo-slidegen/slide-editor/svg";
import {
  EDITOR_STAGE_HEIGHT,
  EDITOR_STAGE_WIDTH,
  type Slide,
  type SlideElement,
} from "@gapo-slidegen/slide-schema";

export type SlideThumbnailProps = {
  slide: Slide;
  resolveAssetUrl?: (assetId: string) => string;
};

function toPercent(value: number, max: number): string {
  return `${(value / max) * 100}%`;
}

function elementStyle(element: SlideElement): React.CSSProperties {
  return {
    position: "absolute",
    left: toPercent(element.position.x, EDITOR_STAGE_WIDTH),
    top: toPercent(element.position.y, EDITOR_STAGE_HEIGHT),
    width: toPercent(element.size.width, EDITOR_STAGE_WIDTH),
    height: toPercent(element.size.height, EDITOR_STAGE_HEIGHT),
    opacity: element.opacity,
    transform: element.rotation ? `rotate(${element.rotation}deg)` : undefined,
    overflow: "hidden",
    pointerEvents: "none",
  };
}

function ThumbnailElement({
  element,
  resolveAssetUrl,
}: {
  element: SlideElement;
  resolveAssetUrl?: ((assetId: string) => string) | undefined;
}) {
  const style = elementStyle(element);

  if (element.type === "text" || element.type === "text-list") {
    const text =
      element.type === "text"
        ? element.runs.map((run) => run.text).join("")
        : element.items.map((item) => item.map((run) => run.text).join(" ")).join("\n");
    const fontSize = Math.max(
      2,
      (element.font?.size ?? 54) * (100 / EDITOR_STAGE_WIDTH),
    );
    const justifyContent =
      element.type === "text"
        ? element.verticalAlign === "middle"
          ? "center"
          : element.verticalAlign === "bottom"
            ? "flex-end"
            : "flex-start"
        : "flex-start";
    return (
      <div
        className="slide-thumbnail__text"
        style={{
          ...style,
          color: element.font?.color ?? "#172033",
          fontFamily: element.font?.family ?? "Arial",
          fontSize: `${fontSize}cqw`,
          fontWeight: element.font?.bold ? "bold" : "normal",
          fontStyle: element.font?.italic ? "italic" : "normal",
          textAlign: element.type === "text" ? element.horizontalAlign : "left",
          lineHeight: element.font?.lineHeight ?? 1.15,
          display: "flex",
          flexDirection: "column",
          justifyContent,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {text}
      </div>
    );
  }

  if (element.type === "shape") {
    const isEllipse = element.shape === "ellipse";
    const borderRadius = isEllipse
      ? "50%"
      : `${Math.min(element.cornerRadius, 4)}px`;
    return (
      <div
        style={{
          ...style,
          backgroundColor: element.fill?.color ?? "transparent",
          borderRadius,
          border:
            element.stroke && element.stroke.width > 0
              ? `${Math.max(1, element.stroke.width)}px solid ${element.stroke.color}`
              : undefined,
        }}
      />
    );
  }

  if (element.type === "image") {
    return (
      <ThumbnailImage
        element={element}
        style={style}
        resolveAssetUrl={resolveAssetUrl}
      />
    );
  }

  if (element.type === "svg") {
    return (
      <img
        src={svgDataUrl(element.svg)}
        alt={element.alt}
        loading="lazy"
        draggable={false}
        style={{
          ...style,
          objectFit: "contain",
        }}
      />
    );
  }

  if (
    element.type === "group" ||
    element.type === "flex" ||
    element.type === "grid" ||
    element.type === "container"
  ) {
    const children =
      element.type === "container"
        ? element.child
          ? [element.child]
          : []
        : element.children;
    return (
      <div style={style}>
        {children.map((child) => (
          <ThumbnailElement
            key={child.id}
            element={child}
            resolveAssetUrl={resolveAssetUrl}
          />
        ))}
      </div>
    );
  }

  return null;
}

function ThumbnailImage({
  element,
  style,
  resolveAssetUrl,
}: {
  element: Extract<SlideElement, { type: "image" }>;
  style: React.CSSProperties;
  resolveAssetUrl?: ((assetId: string) => string) | undefined;
}) {
  const [errored, setErrored] = useState(false);
  const src = resolveAssetUrl?.(element.assetId);

  if (!src || errored) {
    return (
      <div
        style={{
          ...style,
          backgroundColor: "#E9EDF3",
          border: "1px dashed #B8C2D0",
        }}
      />
    );
  }

  return (
    <img
      src={src}
      alt={element.alt}
      loading="lazy"
      draggable={false}
      style={{
        ...style,
        objectFit: element.fit,
      }}
      onError={() => setErrored(true)}
    />
  );
}

export function SlideThumbnail({ slide, resolveAssetUrl }: SlideThumbnailProps) {
  return (
    <div
      className="slide-thumbnail"
      style={{
        backgroundColor: slide.background,
      }}
      aria-hidden="true"
    >
      {slide.elements.map((element) => (
        <ThumbnailElement
          key={element.id}
          element={element}
          resolveAssetUrl={resolveAssetUrl}
        />
      ))}
    </div>
  );
}
