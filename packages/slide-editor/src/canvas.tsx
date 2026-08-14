"use client";

import type Konva from "konva";
import type { KonvaEventObject } from "konva/lib/Node";
import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { Ellipse, Image as KonvaImage, Layer, Line, Rect, Shape as KonvaShape, Stage, Text, Transformer } from "react-konva";
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
  readOnly?: boolean;
  resolveAssetUrl?: (assetId: string) => string;
};

type TextElement = Extract<SlideElement, { type: "text" }>;

type InlineTextEdit = {
  element: TextElement;
  clientX: number;
  clientY: number;
};

function elementFill(element: ShapeElement): string {
  return element.fill?.color ?? "transparent";
}

function ElementNode({
  element,
  onSelect,
  onChange,
  registerNode,
  editingElementId,
  onBeginTextEdit,
  readOnly = false,
  resolveAssetUrl,
}: {
  element: SlideElement;
  onSelect: () => void;
  onChange: (element: SlideElement) => void;
  registerNode: (id: string, node: Konva.Node | null) => void;
  editingElementId: string | null;
  onBeginTextEdit: (element: TextElement, clientX: number, clientY: number) => void;
  readOnly?: boolean;
  resolveAssetUrl?: (assetId: string) => string;
}) {
  const [loadedImage, setLoadedImage] = useState<HTMLImageElement | null>(null);
  const assetId = element.type === "image" ? element.assetId : null;
  useEffect(() => {
    if (!assetId || !resolveAssetUrl) {
      setLoadedImage(null);
      return;
    }
    const image = new window.Image();
    image.onload = () => setLoadedImage(image);
    image.onerror = () => setLoadedImage(null);
    image.src = resolveAssetUrl(assetId);
    return () => {
      image.onload = null;
      image.onerror = null;
    };
  }, [assetId, resolveAssetUrl]);

  const common = {
    id: element.id,
    x: element.position.x,
    y: element.position.y,
    width: element.size.width,
    height: element.size.height,
    rotation: element.rotation,
    opacity: element.opacity,
    draggable: !readOnly && !element.locked && editingElementId !== element.id,
    listening: !readOnly,
    ...(readOnly ? {} : { onClick: onSelect, onTap: onSelect }),
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
        visible={editingElementId !== element.id}
        onDblClick={(event) => {
          onSelect();
          onBeginTextEdit(element, event.evt.clientX, event.evt.clientY);
        }}
        onDblTap={() => {
          onSelect();
          onBeginTextEdit(element, 0, 0);
        }}
        text={text}
        fill={element.font?.color ?? "#172033"}
        fontFamily={element.font?.family ?? "Arial"}
        fontSize={element.font?.size ?? 54}
        fontStyle={[
          element.font?.bold ? "bold" : "",
          element.font?.italic ? "italic" : "",
        ].filter(Boolean).join(" ") || "normal"}
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

    if (element.shape === "triangle" || element.shape === "diamond") {
      return (
        <KonvaShape
          {...common}
          fill={elementFill(element)}
          strokeWidth={element.stroke?.width ?? 0}
          {...(element.stroke ? { stroke: element.stroke.color } : {})}
          sceneFunc={(context, shape) => {
            const width = shape.width();
            const height = shape.height();
            context.beginPath();
            if (element.shape === "triangle") {
              context.moveTo(width / 2, 0);
              context.lineTo(width, height);
              context.lineTo(0, height);
            } else {
              context.moveTo(width / 2, 0);
              context.lineTo(width, height / 2);
              context.lineTo(width / 2, height);
              context.lineTo(0, height / 2);
            }
            context.closePath();
            context.fillStrokeShape(shape);
          }}
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

  if (element.type === "image") {
    if (!loadedImage) {
      return <Rect {...common} fill="#E9EDF3" stroke="#B8C2D0" strokeWidth={2} />;
    }
    const sourceRatio = loadedImage.naturalWidth / loadedImage.naturalHeight;
    const targetRatio = element.size.width / Math.max(1, element.size.height);
    let cropWidth = loadedImage.naturalWidth;
    let cropHeight = loadedImage.naturalHeight;
    if (element.fit === "cover") {
      if (sourceRatio > targetRatio) cropWidth = loadedImage.naturalHeight * targetRatio;
      else cropHeight = loadedImage.naturalWidth / targetRatio;
    }
    const cropX = (loadedImage.naturalWidth - cropWidth) * element.focusX;
    const cropY = (loadedImage.naturalHeight - cropHeight) * element.focusY;
    return (
      <KonvaImage
        {...common}
        image={loadedImage}
        crop={{ x: cropX, y: cropY, width: cropWidth, height: cropHeight }}
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
  readOnly = false,
  resolveAssetUrl,
}: SlideCanvasProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const transformerRef = useRef<Konva.Transformer>(null);
  const nodesRef = useRef(new Map<string, Konva.Node>());
  const inlineEditorRef = useRef<HTMLDivElement>(null);
  const [hostWidth, setHostWidth] = useState<number>(EDITOR_STAGE_WIDTH);
  const [inlineEdit, setInlineEdit] = useState<InlineTextEdit | null>(null);

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
    if (!transformer || readOnly) return;
    const selectedNode = selectedElementId && selectedElementId !== inlineEdit?.element.id
      ? nodesRef.current.get(selectedElementId)
      : undefined;
    transformer.nodes(selectedNode ? [selectedNode] : []);
    transformer.getLayer()?.batchDraw();
  }, [selectedElementId, elements, inlineEdit?.element.id, readOnly]);

  const scale = useMemo(
    () => Math.min(1, Math.max(0.1, hostWidth / EDITOR_STAGE_WIDTH)),
    [hostWidth],
  );

  useEffect(() => {
    const editor = inlineEditorRef.current;
    if (!editor || !inlineEdit) return;
    editor.focus();

    const selection = window.getSelection();
    if (!selection) return;
    const rangeFromPoint = (
      document as Document & {
        caretRangeFromPoint?: (x: number, y: number) => Range | null;
      }
    ).caretRangeFromPoint?.(inlineEdit.clientX, inlineEdit.clientY);
    const caretPosition = document.caretPositionFromPoint?.(
      inlineEdit.clientX,
      inlineEdit.clientY,
    );
    const range = rangeFromPoint ?? (() => {
      if (!caretPosition) return null;
      const nextRange = document.createRange();
      nextRange.setStart(caretPosition.offsetNode, caretPosition.offset);
      nextRange.collapse(true);
      return nextRange;
    })();

    selection.removeAllRanges();
    if (range && editor.contains(range.startContainer)) {
      selection.addRange(range);
      return;
    }
    const fallback = document.createRange();
    fallback.selectNodeContents(editor);
    fallback.collapse(false);
    selection.addRange(fallback);
  }, [inlineEdit?.element.id]);

  useEffect(() => {
    if (inlineEdit && !elements.some((element) => element.id === inlineEdit.element.id)) {
      setInlineEdit(null);
    }
  }, [elements, inlineEdit]);

  function commitInlineEdit(value: string) {
    if (!inlineEdit) return;
    const normalized = value.replace(/\r\n/g, "\n");
    const original = inlineEdit.element.runs.map((run) => run.text).join("");
    if (normalized !== original) {
      const runFont = inlineEdit.element.runs[0]?.font;
      onChangeElement({
        ...inlineEdit.element,
        runs: [{ text: normalized, ...(runFont ? { font: runFont } : {}) }],
      });
    }
    setInlineEdit(null);
  }

  function handleInlineKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    event.stopPropagation();
    if (event.key === "Escape" || ((event.ctrlKey || event.metaKey) && event.key === "Enter")) {
      event.preventDefault();
      event.currentTarget.blur();
    }
  }

  return (
    <div ref={hostRef} style={{ width: "100%", position: "relative" }}>
      <Stage
        width={EDITOR_STAGE_WIDTH * scale}
        height={EDITOR_STAGE_HEIGHT * scale}
        scaleX={scale}
        scaleY={scale}
        onMouseDown={(event) => {
          if (!readOnly && event.target === event.target.getStage()) onSelectElement(null);
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
              editingElementId={inlineEdit?.element.id ?? null}
              onBeginTextEdit={(textElement, clientX, clientY) => {
                setInlineEdit({ element: textElement, clientX, clientY });
              }}
              readOnly={readOnly}
              {...(resolveAssetUrl ? { resolveAssetUrl } : {})}
              registerNode={(id, node) => {
                if (node) nodesRef.current.set(id, node);
                else nodesRef.current.delete(id);
              }}
            />
          ))}
          {!readOnly ? (
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
          ) : null}
        </Layer>
      </Stage>
      {inlineEdit ? (
        <div
          style={{
            position: "absolute",
            left: inlineEdit.element.position.x * scale,
            top: inlineEdit.element.position.y * scale,
            width: inlineEdit.element.size.width * scale,
            height: inlineEdit.element.size.height * scale,
            display: "flex",
            alignItems: inlineEdit.element.verticalAlign === "middle"
              ? "center"
              : inlineEdit.element.verticalAlign === "bottom"
                ? "flex-end"
                : "flex-start",
            boxSizing: "border-box",
            outline: `${Math.max(1, 2 * scale)}px solid #285FC7`,
            outlineOffset: Math.max(1, 2 * scale),
            background: "transparent",
            transform: `rotate(${inlineEdit.element.rotation}deg)`,
            transformOrigin: "top left",
            zIndex: 2,
          }}
        >
          <div
            ref={inlineEditorRef}
            role="textbox"
            aria-label="Edit text on slide"
            aria-multiline="true"
            contentEditable
            suppressContentEditableWarning
            onKeyDown={handleInlineKeyDown}
            onBlur={(event) => commitInlineEdit(event.currentTarget.innerText)}
            onPaste={(event) => {
              event.preventDefault();
              const selection = window.getSelection();
              if (!selection?.rangeCount) return;
              const range = selection.getRangeAt(0);
              if (!event.currentTarget.contains(range.commonAncestorContainer)) return;
              range.deleteContents();
              const pastedText = document.createTextNode(
                event.clipboardData.getData("text/plain"),
              );
              range.insertNode(pastedText);
              range.setStartAfter(pastedText);
              range.collapse(true);
              selection.removeAllRanges();
              selection.addRange(range);
            }}
            style={{
              width: "100%",
              maxHeight: "100%",
              color: inlineEdit.element.font?.color ?? "#172033",
              fontFamily: inlineEdit.element.font?.family ?? "Arial",
              fontSize: (inlineEdit.element.font?.size ?? 54) * scale,
              fontWeight: inlineEdit.element.font?.bold ? 700 : 400,
              fontStyle: inlineEdit.element.font?.italic ? "italic" : "normal",
              lineHeight: inlineEdit.element.font?.lineHeight ?? 1.15,
              letterSpacing: (inlineEdit.element.font?.letterSpacing ?? 0) * scale,
              textAlign: inlineEdit.element.horizontalAlign,
              whiteSpace: "pre-wrap",
              overflow: "hidden",
              overflowWrap: "break-word",
              boxSizing: "border-box",
              padding: 0,
              margin: 0,
              border: "none",
              outline: "none",
              background: "transparent",
              cursor: "text",
            }}
          >
            {inlineEdit.element.runs.map((run) => run.text).join("")}
          </div>
        </div>
      ) : null}
    </div>
  );
}
