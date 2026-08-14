"use client";

import type Konva from "konva";
import type { KonvaEventObject } from "konva/lib/Node";
import { useEffect, useMemo, useRef, useState } from "react";
import { Ellipse, Layer, Line, Rect, Stage, Text, Transformer } from "react-konva";
import {
  EDITOR_STAGE_HEIGHT,
  EDITOR_STAGE_WIDTH,
  type ShapeElement,
  type SlideElement,
} from "@gapo-slidegen/slide-schema";

export type SlideCanvasProps = {
  elements: SlideElement[];
  background: string;
  selectedElementId: string | null;
  onSelectElement: (elementId: string | null) => void;
  onChangeElement: (element: SlideElement) => void;
};

function elementFill(element: ShapeElement): string {
  return element.fill?.color ?? "transparent";
}

function ElementNode({
  element,
  onSelect,
  onChange,
  registerNode,
}: {
  element: SlideElement;
  onSelect: () => void;
  onChange: (element: SlideElement) => void;
  registerNode: (id: string, node: Konva.Node | null) => void;
}) {
  const common = {
    id: element.id,
    x: element.position.x,
    y: element.position.y,
    width: element.size.width,
    height: element.size.height,
    rotation: element.rotation,
    opacity: element.opacity,
    draggable: !element.locked,
    onClick: onSelect,
    onTap: onSelect,
    onDragEnd: (event: KonvaEventObject<DragEvent>) => {
      onChange({
        ...element,
        position: { x: event.target.x(), y: event.target.y() },
      });
    },
    onTransformEnd: (event: KonvaEventObject<Event>) => {
      const node = event.target;
      const scaleX = node.scaleX();
      const scaleY = node.scaleY();
      node.scaleX(1);
      node.scaleY(1);
      onChange({
        ...element,
        position: { x: node.x(), y: node.y() },
        size: {
          width: Math.max(1, node.width() * scaleX),
          height: Math.max(1, node.height() * scaleY),
        },
        rotation: node.rotation(),
      });
    },
    ref: (node: Konva.Node | null) => registerNode(element.id, node),
  };

  if (element.type === "text") {
    const text = element.runs.map((run) => run.text).join("");
    return (
      <Text
        {...common}
        text={text}
        fill={element.font?.color ?? "#172033"}
        fontFamily={element.font?.family ?? "Arial"}
        fontSize={element.font?.size ?? 54}
        fontStyle={element.font?.bold ? "bold" : "normal"}
        lineHeight={element.font?.lineHeight ?? 1.15}
        align={element.horizontalAlign}
        verticalAlign={element.verticalAlign === "middle" ? "middle" : element.verticalAlign}
      />
    );
  }

  if (element.type === "shape") {
    if (element.shape === "ellipse") {
      return (
        <Ellipse
          {...common}
          x={element.position.x + element.size.width / 2}
          y={element.position.y + element.size.height / 2}
          radiusX={element.size.width / 2}
          radiusY={element.size.height / 2}
          fill={elementFill(element)}
          strokeWidth={element.stroke?.width ?? 0}
          {...(element.stroke ? { stroke: element.stroke.color } : {})}
        />
      );
    }

    return (
      <Rect
        {...common}
        fill={elementFill(element)}
        strokeWidth={element.stroke?.width ?? 0}
        cornerRadius={element.cornerRadius}
        {...(element.stroke ? { stroke: element.stroke.color } : {})}
      />
    );
  }

  if (element.type === "line") {
    return (
      <Line
        {...common}
        points={[0, 0, element.size.width, element.size.height]}
        stroke={element.stroke.color}
        strokeWidth={element.stroke.width}
        {...(element.stroke.dash ? { dash: element.stroke.dash } : {})}
      />
    );
  }

  return (
    <Rect
      {...common}
      fill="#E9EDF3"
      stroke="#B8C2D0"
      strokeWidth={2}
      dash={[10, 8]}
    />
  );
}

export function SlideCanvas({
  elements,
  background,
  selectedElementId,
  onSelectElement,
  onChangeElement,
}: SlideCanvasProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const transformerRef = useRef<Konva.Transformer>(null);
  const nodesRef = useRef(new Map<string, Konva.Node>());
  const [hostWidth, setHostWidth] = useState<number>(EDITOR_STAGE_WIDTH);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry) setHostWidth(entry.contentRect.width);
    });
    observer.observe(host);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const transformer = transformerRef.current;
    if (!transformer) return;
    const selectedNode = selectedElementId
      ? nodesRef.current.get(selectedElementId)
      : undefined;
    transformer.nodes(selectedNode ? [selectedNode] : []);
    transformer.getLayer()?.batchDraw();
  }, [selectedElementId, elements]);

  const scale = useMemo(
    () => Math.min(1, Math.max(0.1, hostWidth / EDITOR_STAGE_WIDTH)),
    [hostWidth],
  );

  return (
    <div ref={hostRef} style={{ width: "100%" }}>
      <Stage
        width={EDITOR_STAGE_WIDTH * scale}
        height={EDITOR_STAGE_HEIGHT * scale}
        scaleX={scale}
        scaleY={scale}
        onMouseDown={(event) => {
          if (event.target === event.target.getStage()) onSelectElement(null);
        }}
      >
        <Layer>
          <Rect
            width={EDITOR_STAGE_WIDTH}
            height={EDITOR_STAGE_HEIGHT}
            fill={background}
            listening={false}
          />
          {elements.map((element) => (
            <ElementNode
              key={element.id}
              element={element}
              onSelect={() => onSelectElement(element.id)}
              onChange={onChangeElement}
              registerNode={(id, node) => {
                if (node) nodesRef.current.set(id, node);
                else nodesRef.current.delete(id);
              }}
            />
          ))}
          <Transformer
            ref={transformerRef}
            rotateEnabled
            flipEnabled={false}
            borderStroke="#285FC7"
            anchorStroke="#285FC7"
            anchorFill="#FFFFFF"
            anchorSize={10}
            boundBoxFunc={(oldBox, nextBox) =>
              nextBox.width < 8 || nextBox.height < 8 ? oldBox : nextBox
            }
          />
        </Layer>
      </Stage>
    </div>
  );
}
