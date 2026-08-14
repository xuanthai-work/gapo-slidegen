"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import {
  ArrowDown,
  ArrowClockwise,
  ArrowCounterClockwise,
  ArrowLeft,
  ArrowUp,
  CaretLeft,
  CaretRight,
  Copy,
  DownloadSimple,
  ImageSquare,
  Play,
  Plus,
  Sparkle,
  Square,
  TextT,
  Trash,
  X,
} from "@phosphor-icons/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { EditorBoundary } from "@gapo-slidegen/slide-editor";
import { canonicalPresentationFixture } from "@gapo-slidegen/slide-schema/fixtures";
import {
  parsePresentation,
  type EditOperation,
  type Presentation,
  type Slide,
  type SlideElement,
} from "@gapo-slidegen/slide-schema";
import { ApiError, apiFetch, type StoredAsset, type StoredPresentation } from "../lib/api";

const SlideCanvas = dynamic(() => import("./editor-canvas"), { ssr: false });
const resolveAssetUrl = (assetId: string) => `/api/backend/v1/assets/${assetId}/content`;
type TextElement = Extract<SlideElement, { type: "text" }>;

function collectTextElements(elements: SlideElement[]): TextElement[] {
  return elements.flatMap((element) => {
    if (element.type === "text") return [element];
    if ("children" in element) return collectTextElements(element.children);
    return [];
  });
}

function rewriteTextElements(
  elements: SlideElement[],
  rewrittenById: ReadonlyMap<string, string>,
): SlideElement[] {
  return elements.map((element) => {
    if (element.type === "text") {
      const text = rewrittenById.get(element.id);
      if (text === undefined) return element;
      const runFont = element.runs[0]?.font;
      return {
        ...element,
        runs: [{ text, ...(runFont ? { font: runFont } : {}) }],
      };
    }
    if ("children" in element) {
      return {
        ...element,
        children: rewriteTextElements(element.children, rewrittenById),
      } as SlideElement;
    }
    return element;
  });
}

export function EditorSpike({ presentationId }: { presentationId: string | undefined }) {
  const [initialDocument, setInitialDocument] = useState<Presentation>(() =>
    structuredClone(canonicalPresentationFixture),
  );
  const [document, setDocument] = useState<Presentation>(() =>
    structuredClone(canonicalPresentationFixture),
  );
  const [titleDraft, setTitleDraft] = useState(canonicalPresentationFixture.title);
  const [selectedElementId, setSelectedElementId] = useState<string | null>("title");
  const [activeSlideIndex, setActiveSlideIndex] = useState(0);
  const [presenting, setPresenting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [panelTab, setPanelTab] = useState<"properties" | "ai">("properties");
  const [aiTool, setAiTool] = useState<"rewrite" | "image">("rewrite");
  const [aiScope, setAiScope] = useState<"selection" | "slide">("selection");
  const [aiInstruction, setAiInstruction] = useState("");
  const [imagePrompt, setImagePrompt] = useState("");
  const [rewritingWithAI, setRewritingWithAI] = useState(false);
  const [generatingImage, setGeneratingImage] = useState(false);
  const [, setHistoryVersion] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState(presentationId ? "Loading…" : "Saved locally");
  const revisionRef = useRef(0);
  const readyRef = useRef(false);
  const skipNextDocumentRef = useRef(false);
  const pendingDocumentRef = useRef<Presentation | null>(null);
  const savingRef = useRef(false);
  const saveBlockedRef = useRef(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const editor = useMemo(
    () =>
      new EditorBoundary({
        initialDocument,
        onChange: ({ document: nextDocument }) => {
          setDocument(nextDocument);
          setHistoryVersion((current) => current + 1);
        },
      }),
    [initialDocument],
  );
  const slide = document.slides[activeSlideIndex];
  const selected = slide?.elements.find((element) => element.id === selectedElementId);
  const slideTextElements = slide ? collectTextElements(slide.elements) : [];

  useEffect(() => setTitleDraft(document.title), [document.title]);

  useEffect(() => {
    if (!presentationId) return;
    readyRef.current = false;
    saveBlockedRef.current = false;
    setSaveState("Loading…");
    apiFetch<StoredPresentation>(`/v1/presentations/${presentationId}`)
      .then((stored) => {
        const parsed = parsePresentation(stored.document);
        revisionRef.current = stored.revision;
        skipNextDocumentRef.current = true;
        readyRef.current = true;
        setInitialDocument(parsed);
        setDocument(parsed);
        setActiveSlideIndex(0);
        setSelectedElementId(parsed.slides[0]?.elements[0]?.id ?? null);
        setSaveState("Saved");
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 401) {
          window.location.replace("/login");
          return;
        }
        setLoadError(caught instanceof Error ? caught.message : "Could not load presentation.");
      });
  }, [presentationId]);

  async function flushPendingSave() {
    if (!presentationId || savingRef.current || saveBlockedRef.current) return;
    const pending = pendingDocumentRef.current;
    if (!pending) return;

    pendingDocumentRef.current = null;
    savingRef.current = true;
    let continueSaving = true;
    setSaveState("Saving…");
    try {
      const stored = await apiFetch<StoredPresentation>(`/v1/presentations/${presentationId}`, {
        method: "PATCH",
        body: JSON.stringify({
          expected_revision: revisionRef.current,
          document: pending,
        }),
      });
      revisionRef.current = stored.revision;
      setSaveState(pendingDocumentRef.current ? "Unsaved changes" : "Saved");
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        continueSaving = false;
        saveBlockedRef.current = true;
        setSaveState("Conflict, reload required");
      } else if (caught instanceof ApiError && caught.status === 401) {
        continueSaving = false;
        window.location.replace("/login");
      } else {
        continueSaving = false;
        pendingDocumentRef.current = pending;
        setSaveState("Save failed");
      }
    } finally {
      savingRef.current = false;
      if (continueSaving && pendingDocumentRef.current && !saveBlockedRef.current) {
        void flushPendingSave();
      }
    }
  }

  useEffect(() => {
    if (!presentationId || !readyRef.current) return;
    if (skipNextDocumentRef.current) {
      skipNextDocumentRef.current = false;
      return;
    }
    pendingDocumentRef.current = document;
    setSaveState("Unsaved changes");
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => void flushPendingSave(), 700);
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [document, presentationId]);

  useEffect(() => {
    if (!presenting) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setPresenting(false);
      if (event.key === "ArrowRight" || event.key === " ") {
        event.preventDefault();
        setActiveSlideIndex((current) => Math.min(document.slides.length - 1, current + 1));
      }
      if (event.key === "ArrowLeft") {
        setActiveSlideIndex((current) => Math.max(0, current - 1));
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [document.slides.length, presenting]);

  useEffect(() => {
    function onHistoryKeyDown(event: KeyboardEvent) {
      if (!(event.ctrlKey || event.metaKey)) return;
      const target = event.target;
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) return;
      const key = event.key.toLowerCase();
      if (key === "z" && event.shiftKey) {
        event.preventDefault();
        applyHistory("redo");
      } else if (key === "z") {
        event.preventDefault();
        applyHistory("undo");
      } else if (key === "y") {
        event.preventDefault();
        applyHistory("redo");
      }
    }
    window.addEventListener("keydown", onHistoryKeyDown);
    return () => window.removeEventListener("keydown", onHistoryKeyDown);
  }, [editor]);

  useEffect(() => {
    function onElementKeyDown(event: KeyboardEvent) {
      const target = event.target;
      if (
        target instanceof HTMLInputElement
        || target instanceof HTMLTextAreaElement
        || target instanceof HTMLSelectElement
        || (target instanceof HTMLElement && target.isContentEditable)
      ) return;
      if ((event.key === "Delete" || event.key === "Backspace") && selectedElementId) {
        event.preventDefault();
        removeSelectedElement();
      } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "d" && selected) {
        event.preventDefault();
        duplicateSelectedElement();
      }
    }
    window.addEventListener("keydown", onElementKeyDown);
    return () => window.removeEventListener("keydown", onElementKeyDown);
  }, [editor, selected, selectedElementId, slide]);

  function applyHistory(direction: "undo" | "redo") {
    const next = direction === "undo" ? editor.undo() : editor.redo();
    if (!next) return;
    setActiveSlideIndex((current) => Math.min(current, next.slides.length - 1));
    setSelectedElementId(null);
  }

  async function exportPptx() {
    setExporting(true);
    setActionError(null);
    try {
      const response = await fetch("/api/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(document),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? "Could not export the presentation.");
      }
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition");
      const filename = disposition?.match(/filename="([^"]+)"/)?.[1] ?? "presentation.pptx";
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "Could not export the presentation.");
    } finally {
      setExporting(false);
    }
  }

  function applyOperation(operation: EditOperation): boolean {
    try {
      editor.apply(operation);
      setActionError(null);
      return true;
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "Could not edit the presentation.");
      return false;
    }
  }

  function commitTitle() {
    const title = titleDraft.trim();
    if (!title) {
      setTitleDraft(document.title);
      return;
    }
    if (title === document.title) {
      setTitleDraft(title);
      return;
    }
    if (!applyOperation({
      operationId: crypto.randomUUID(),
      type: "replace-presentation",
      presentation: { ...document, title },
    })) {
      setTitleDraft(document.title);
    }
  }

  function addSlide() {
    const id = crypto.randomUUID();
    const nextIndex = activeSlideIndex + 1;
    const newSlide: Slide = {
      id,
      title: "Untitled slide",
      background: document.theme.colors.surface,
      revision: 0,
      elements: [
        {
          id: crypto.randomUUID(),
          type: "text",
          position: { x: 96, y: 92 },
          size: { width: 900, height: 130 },
          rotation: 0,
          opacity: 1,
          locked: false,
          decorative: false,
          runs: [{ text: "Untitled slide" }],
          font: {
            family: document.theme.fonts.heading,
            size: 52,
            color: document.theme.colors.text,
            bold: true,
          },
          horizontalAlign: "left",
          verticalAlign: "top",
        },
      ],
    };
    if (
      applyOperation({
        operationId: crypto.randomUUID(),
        type: "add-slide",
        index: nextIndex,
        slide: newSlide,
      })
    ) {
      setActiveSlideIndex(nextIndex);
      setSelectedElementId(newSlide.elements[0]?.id ?? null);
    }
  }

  function removeSlide(index: number) {
    const target = document.slides[index];
    if (!target || document.slides.length === 1) return;
    if (
      applyOperation({
        operationId: crypto.randomUUID(),
        type: "remove-slide",
        slideId: target.id,
      })
    ) {
      const nextIndex = Math.min(index, document.slides.length - 2);
      const nextSlide = document.slides[index + 1] ?? document.slides[index - 1];
      setActiveSlideIndex(nextIndex);
      setSelectedElementId(nextSlide?.elements[0]?.id ?? null);
    }
  }

  function moveSlide(index: number, direction: -1 | 1) {
    const target = document.slides[index];
    const nextIndex = index + direction;
    if (!target || nextIndex < 0 || nextIndex >= document.slides.length) return;
    if (
      applyOperation({
        operationId: crypto.randomUUID(),
        type: "move-slide",
        slideId: target.id,
        index: nextIndex,
      })
    ) {
      setActiveSlideIndex(nextIndex);
    }
  }

  function insertText() {
    if (!slide) return;
    const id = crypto.randomUUID();
    const element: SlideElement = {
      id,
      type: "text",
      position: { x: 120, y: 250 },
      size: { width: 620, height: 100 },
      rotation: 0,
      opacity: 1,
      locked: false,
      decorative: false,
      runs: [{ text: "Add your text" }],
      font: {
        family: document.theme.fonts.body,
        size: 32,
        color: document.theme.colors.text,
      },
      horizontalAlign: "left",
      verticalAlign: "top",
    };
    if (applyOperation({ operationId: crypto.randomUUID(), type: "upsert-element", slideId: slide.id, element })) {
      setSelectedElementId(id);
    }
  }

  function insertShape() {
    if (!slide) return;
    const id = crypto.randomUUID();
    const element: SlideElement = {
      id,
      type: "shape",
      position: { x: 440, y: 300 },
      size: { width: 280, height: 150 },
      rotation: 0,
      opacity: 1,
      locked: false,
      decorative: false,
      shape: "rectangle",
      fill: { color: document.theme.colors.primary, opacity: 1 },
      cornerRadius: 12,
    };
    if (applyOperation({ operationId: crypto.randomUUID(), type: "upsert-element", slideId: slide.id, element })) {
      setSelectedElementId(id);
    }
  }

  function placeImageAsset(
    targetSlide: Slide,
    asset: StoredAsset,
    alt: string,
    targetImage: Extract<SlideElement, { type: "image" }> | null = null,
  ) {
    if (targetImage) {
      applyOperation({
        operationId: crypto.randomUUID(),
        type: "upsert-element",
        slideId: targetSlide.id,
        element: { ...targetImage, assetId: asset.id, alt },
      });
      return;
    }
    const id = crypto.randomUUID();
    const element: SlideElement = {
      id,
      type: "image",
      position: { x: 240, y: 150 },
      size: { width: 640, height: 360 },
      rotation: 0,
      opacity: 1,
      locked: false,
      decorative: false,
      assetId: asset.id,
      fit: "cover",
      focusX: 0.5,
      focusY: 0.5,
      cropScale: 1,
      flipHorizontal: false,
      flipVertical: false,
      alt,
    };
    if (
      applyOperation({
        operationId: crypto.randomUUID(),
        type: "upsert-element",
        slideId: targetSlide.id,
        element,
      })
    ) {
      setSelectedElementId(id);
    }
  }

  async function uploadImage(file: File) {
    if (!slide) return;
    const targetSlide = slide;
    setUploadingImage(true);
    setActionError(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const asset = await apiFetch<StoredAsset>("/v1/assets", { method: "POST", body });
      placeImageAsset(targetSlide, asset, asset.filename);
    } catch (caught) {
      setActionError(caught instanceof ApiError ? caught.message : "Could not upload the image.");
    } finally {
      setUploadingImage(false);
      if (imageInputRef.current) imageInputRef.current.value = "";
    }
  }

  async function generateImage() {
    const prompt = imagePrompt.trim();
    if (!slide || !prompt) return;
    const targetSlide = slide;
    const targetImage = selected?.type === "image" ? selected : null;
    setGeneratingImage(true);
    setActionError(null);
    try {
      const asset = await apiFetch<StoredAsset>("/v1/assets/generate", {
        method: "POST",
        body: JSON.stringify({ prompt, aspect_ratio: "16:9" }),
      });
      placeImageAsset(targetSlide, asset, prompt, targetImage);
      setImagePrompt("");
    } catch (caught) {
      setActionError(caught instanceof ApiError ? caught.message : "Could not generate the image.");
    } finally {
      setGeneratingImage(false);
    }
  }

  function removeSelectedElement() {
    if (!slide || !selectedElementId) return;
    if (
      applyOperation({
        operationId: crypto.randomUUID(),
        type: "remove-element",
        slideId: slide.id,
        elementId: selectedElementId,
      })
    ) {
      setSelectedElementId(null);
    }
  }

  function duplicateSelectedElement() {
    if (!slide || !selected) return;
    const id = crypto.randomUUID();
    const element = structuredClone(selected);
    element.id = id;
    element.position = {
      x: Math.min(1240 - element.size.width, Math.max(0, element.position.x + 24)),
      y: Math.min(680 - element.size.height, Math.max(0, element.position.y + 24)),
    };
    if (applyOperation({
      operationId: crypto.randomUUID(),
      type: "upsert-element",
      slideId: slide.id,
      element,
    })) setSelectedElementId(id);
  }

  function moveSelectedElement(direction: -1 | 1) {
    if (!slide || !selected) return;
    const currentIndex = slide.elements.findIndex((element) => element.id === selected.id);
    const nextIndex = currentIndex + direction;
    if (currentIndex < 0 || nextIndex < 0 || nextIndex >= slide.elements.length) return;
    applyOperation({
      operationId: crypto.randomUUID(),
      type: "move-element",
      slideId: slide.id,
      elementId: selected.id,
      index: nextIndex,
    });
  }

  function updateElement(element: SlideElement) {
    if (!slide) return;
    editor.apply({
      operationId: crypto.randomUUID(),
      type: "upsert-element",
      slideId: slide.id,
      element,
    });
  }

  function updateSelectedText(value: string) {
    if (!selected || selected.type !== "text") return;
    const runFont = selected.runs[0]?.font;
    updateElement({
      ...selected,
      runs: [{ text: value, ...(runFont ? { font: runFont } : {}) }],
    });
  }

  function updateSelectedTextFont(
    patch: Partial<NonNullable<Extract<SlideElement, { type: "text" }>["font"]>>,
  ) {
    if (!selected || selected.type !== "text") return;
    updateElement({ ...selected, font: { ...selected.font, ...patch } });
  }

  function updateSelectedImage(
    patch: Partial<Pick<Extract<SlideElement, { type: "image" }>, "alt" | "fit">>,
  ) {
    if (!selected || selected.type !== "image") return;
    updateElement({ ...selected, ...patch });
  }

  function updateSelectedShape(
    patch: Partial<Pick<Extract<SlideElement, { type: "shape" }>, "cornerRadius" | "fill" | "shape">>,
  ) {
    if (!selected || selected.type !== "shape") return;
    updateElement({ ...selected, ...patch });
  }

  async function rewriteWithAI() {
    const instruction = aiInstruction.trim();
    if (!slide || !instruction) return;
    if (aiScope === "selection" && (!selected || selected.type !== "text")) return;
    if (aiScope === "slide" && slideTextElements.length === 0) return;
    setRewritingWithAI(true);
    setActionError(null);
    try {
      if (aiScope === "selection" && selected?.type === "text") {
        const result = await apiFetch<{ text: string; provider: string }>("/v1/ai/rewrite", {
          method: "POST",
          body: JSON.stringify({
            text: selected.runs.map((run) => run.text).join(""),
            instruction,
            language: document.language,
          }),
        });
        updateSelectedText(result.text);
      } else {
        const result = await apiFetch<{
          items: Array<{ id: string; text: string }>;
          provider: string;
        }>("/v1/ai/rewrite-slide", {
          method: "POST",
          body: JSON.stringify({
            items: slideTextElements.map((element) => ({
              id: element.id,
              text: element.runs.map((run) => run.text).join(""),
            })),
            instruction,
            language: document.language,
          }),
        });
        const rewrittenById = new Map(result.items.map((item) => [item.id, item.text]));
        const rewrittenSlide: Slide = {
          ...slide,
          elements: rewriteTextElements(slide.elements, rewrittenById),
        };
        applyOperation({
          operationId: crypto.randomUUID(),
          type: "replace-slide",
          slideId: slide.id,
          slide: rewrittenSlide,
        });
      }
      setAiInstruction("");
    } catch (caught) {
      setActionError(caught instanceof ApiError ? caught.message : "Could not rewrite the slide content.");
    } finally {
      setRewritingWithAI(false);
    }
  }

  function renderElementActions() {
    if (!selected || !slide) return null;
    const index = slide.elements.findIndex((element) => element.id === selected.id);
    return (
      <>
        <div className="element-actions" aria-label="Element actions">
          <button type="button" title="Duplicate (Ctrl+D)" onClick={duplicateSelectedElement}>
            <Copy size={15} />Duplicate
          </button>
          <button type="button" title="Send backward" disabled={index <= 0} onClick={() => moveSelectedElement(-1)}>
            <ArrowDown size={15} />Back
          </button>
          <button type="button" title="Bring forward" disabled={index >= slide.elements.length - 1} onClick={() => moveSelectedElement(1)}>
            <ArrowUp size={15} />Front
          </button>
        </div>
        <button className="delete-element" title="Delete (Del)" onClick={removeSelectedElement}>
          <Trash size={15} />Delete element
        </button>
      </>
    );
  }

  if (loadError) return <main className="empty">{loadError}</main>;
  if (!slide) return <main className="empty">No slide is available.</main>;

  return (
    <main className="editor-shell">
      <header className="topbar">
        <div className="topbar__leading">
          <Link className="icon-button" href="/" aria-label="Back to presentations">
            <ArrowLeft size={18} />
          </Link>
          <span className="wordmark">Gapo SlideGen</span>
          <input
            className="document-title-input"
            aria-label="Presentation title"
            value={titleDraft}
            maxLength={500}
            title="Rename presentation"
            onChange={(event) => setTitleDraft(event.target.value)}
            onBlur={commitTitle}
            onKeyDown={(event) => {
              if (event.key === "Enter") event.currentTarget.blur();
              if (event.key === "Escape") {
                setTitleDraft(document.title);
                event.currentTarget.blur();
              }
            }}
          />
          <span className="save-state">{saveState}</span>
          <span className="history-controls" aria-label="Edit history">
            <button aria-label="Undo" title="Undo (Ctrl+Z)" disabled={!editor.canUndo} onClick={() => applyHistory("undo")}><ArrowCounterClockwise size={16} /></button>
            <button aria-label="Redo" title="Redo (Ctrl+Shift+Z)" disabled={!editor.canRedo} onClick={() => applyHistory("redo")}><ArrowClockwise size={16} /></button>
          </span>
        </div>
        <div className="topbar__actions">
          <button className="button button--quiet" onClick={() => setPresenting(true)}><Play size={17} />Present</button>
          <button className="button button--primary" disabled={exporting} onClick={() => void exportPptx()}>
            <DownloadSimple size={17} />{exporting ? "Exporting…" : "Export PPTX"}
          </button>
        </div>
      </header>

      <section className="editor-grid">
        <aside className="filmstrip" aria-label="Slides">
          <h2>Slides</h2>
          {document.slides.map((item, index) => {
            const preview = item.elements.find((element) => element.type === "text");
            return (
              <div className="thumbnail-row" key={item.id}>
                <button
                  className={`thumbnail${index === activeSlideIndex ? " thumbnail--active" : ""}`}
                  aria-label={`Open slide ${index + 1}`}
                  onClick={() => {
                    setActiveSlideIndex(index);
                    setSelectedElementId(item.elements[0]?.id ?? null);
                  }}
                >
                  <span className="thumbnail__number">{index + 1}</span>
                  <span className="thumbnail__preview">
                    {preview?.type === "text" ? preview.runs.map((run) => run.text).join("") : `Slide ${index + 1}`}
                  </span>
                </button>
                {index === activeSlideIndex ? (
                  <div className="thumbnail-actions" aria-label={`Actions for slide ${index + 1}`}>
                    <button aria-label="Move slide up" disabled={index === 0} onClick={() => moveSlide(index, -1)}><ArrowUp size={14} /></button>
                    <button aria-label="Move slide down" disabled={index === document.slides.length - 1} onClick={() => moveSlide(index, 1)}><ArrowDown size={14} /></button>
                    <button aria-label="Delete slide" disabled={document.slides.length === 1} onClick={() => removeSlide(index)}><Trash size={14} /></button>
                  </div>
                ) : null}
              </div>
            );
          })}
          <button className="add-slide" disabled={document.slides.length >= 30} onClick={addSlide}>
            <Plus size={15} /> Add slide
          </button>
        </aside>

        <section className="workspace" aria-label="Slide canvas">
          <div className="insert-bar">
            <span className="insert-bar__label">Insert</span>
            <button onClick={insertText}><TextT size={16} />Text</button>
            <button onClick={insertShape}><Square size={16} />Shape</button>
            <input
              ref={imageInputRef}
              className="visually-hidden"
              id="editor-image-upload"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void uploadImage(file);
              }}
            />
            <button disabled={uploadingImage} onClick={() => imageInputRef.current?.click()}>
              <ImageSquare size={16} />{uploadingImage ? "Uploading…" : "Image"}
            </button>
          </div>
          <div className="canvas-frame">
            <SlideCanvas
              elements={slide.elements}
              background={slide.background}
              selectedElementId={selectedElementId}
              onSelectElement={setSelectedElementId}
              onChangeElement={updateElement}
              resolveAssetUrl={resolveAssetUrl}
            />
          </div>
          <div className="zoom-control">Fit to workspace</div>
        </section>

        <aside className="properties">
          <div className="panel-tabs">
            <button className={panelTab === "properties" ? "is-active" : ""} onClick={() => setPanelTab("properties")}>Properties</button>
            <button className={panelTab === "ai" ? "is-active" : ""} onClick={() => setPanelTab("ai")}>AI</button>
          </div>
          {panelTab === "ai" ? (
            <div className="ai-rewrite-panel">
              <span className="ai-rewrite-panel__icon"><Sparkle size={19} /></span>
              <h2>{aiTool === "rewrite" ? "Rewrite with AI" : "Generate an image"}</h2>
              <div className="ai-tool-tabs" aria-label="AI tool">
                <button
                  type="button"
                  className={aiTool === "rewrite" ? "is-active" : ""}
                  aria-pressed={aiTool === "rewrite"}
                  onClick={() => setAiTool("rewrite")}
                >
                  Rewrite
                </button>
                <button
                  type="button"
                  className={aiTool === "image" ? "is-active" : ""}
                  aria-pressed={aiTool === "image"}
                  onClick={() => setAiTool("image")}
                >
                  Image
                </button>
              </div>
              {aiTool === "image" ? (
                <>
                  <p>
                    {selected?.type === "image"
                      ? "The generated image will replace the selected image while keeping its frame."
                      : "A new 16:9 image will be added to the current slide."}
                  </p>
                  <label htmlFor="ai-image-prompt">Image prompt</label>
                  <textarea
                    id="ai-image-prompt"
                    value={imagePrompt}
                    maxLength={2000}
                    placeholder="A restrained editorial illustration of a team planning a product launch, warm natural light…"
                    onChange={(event) => setImagePrompt(event.target.value)}
                  />
                  <div className="ai-presets" aria-label="Image prompt suggestions">
                    <button type="button" onClick={() => setImagePrompt("A clean editorial illustration, minimal composition, no text")}>Editorial</button>
                    <button type="button" onClick={() => setImagePrompt("A realistic professional photograph, natural light, no text or logos")}>Photo</button>
                    <button type="button" onClick={() => setImagePrompt("A simple conceptual diagram illustration, clear visual hierarchy, no text")}>Concept</button>
                  </div>
                  <button className="button button--primary ai-rewrite-submit" disabled={generatingImage || !imagePrompt.trim()} onClick={() => void generateImage()}>
                    <ImageSquare size={16} />{generatingImage ? "Generating…" : selected?.type === "image" ? "Generate and replace" : "Generate and add"}
                  </button>
                  <small>Only this prompt is sent to the configured image provider. The result is stored as your private asset.</small>
                </>
              ) : (
                <>
                  <div className="ai-scope" aria-label="Rewrite scope">
                    <button
                      type="button"
                      className={aiScope === "selection" ? "is-active" : ""}
                      aria-pressed={aiScope === "selection"}
                      onClick={() => setAiScope("selection")}
                    >
                      Selected text
                    </button>
                    <button
                      type="button"
                      className={aiScope === "slide" ? "is-active" : ""}
                      aria-pressed={aiScope === "slide"}
                      onClick={() => setAiScope("slide")}
                    >
                      Current slide
                    </button>
                  </div>
                  {(aiScope === "selection" && selected?.type === "text") || (aiScope === "slide" && slideTextElements.length > 0) ? (
                    <>
                      <p className="ai-selection-preview">
                        {aiScope === "selection" && selected?.type === "text"
                          ? selected.runs.map((run) => run.text).join("")
                          : `${slideTextElements.length} editable text block${slideTextElements.length === 1 ? "" : "s"} will be rewritten together.`}
                      </p>
                      <label htmlFor="ai-rewrite-instruction">Instruction</label>
                      <textarea
                        id="ai-rewrite-instruction"
                        value={aiInstruction}
                        maxLength={2000}
                        placeholder="Make this shorter and more persuasive…"
                        onChange={(event) => setAiInstruction(event.target.value)}
                      />
                      <div className="ai-presets" aria-label="Rewrite suggestions">
                        <button type="button" onClick={() => setAiInstruction("Make this shorter and clearer")}>Shorten</button>
                        <button type="button" onClick={() => setAiInstruction("Rewrite this in a professional presentation tone")}>Professional</button>
                        <button type="button" onClick={() => setAiInstruction("Turn this into a strong, concise key message")}>Key message</button>
                      </div>
                      <button className="button button--primary ai-rewrite-submit" disabled={rewritingWithAI || !aiInstruction.trim()} onClick={() => void rewriteWithAI()}>
                        <Sparkle size={16} />{rewritingWithAI ? "Rewriting…" : "Apply rewrite"}
                      </button>
                      <small>
                        {aiScope === "selection"
                          ? "Only the selected text is sent to the configured AI provider."
                          : "Only this slide's text is sent. Layout, styles, and element identities stay local."}
                      </small>
                    </>
                  ) : (
                    <p>
                      {aiScope === "selection"
                        ? "Select a text element on the slide to rewrite it with a prompt."
                        : "This slide has no editable text blocks."}
                    </p>
                  )}
                </>
              )}
            </div>
          ) : selected?.type === "text" ? (
            <div className="property-form">
              <label htmlFor="selected-text">Text</label>
              <textarea
                id="selected-text"
                value={selected.runs.map((run) => run.text).join("")}
                onChange={(event) => updateSelectedText(event.target.value)}
              />
              <div className="property-grid">
                <label>
                  <span>Size</span>
                  <input
                    type="number"
                    min="8"
                    max="200"
                    value={selected.font?.size ?? 54}
                    onChange={(event) => {
                      const size = Number(event.target.value);
                      if (Number.isFinite(size)) updateSelectedTextFont({ size: Math.min(200, Math.max(8, size)) });
                    }}
                  />
                </label>
                <label>
                  <span>Color</span>
                  <span className="color-field">
                    <input
                      aria-label="Text color"
                      type="color"
                      value={selected.font?.color ?? document.theme.colors.text}
                      onChange={(event) => updateSelectedTextFont({ color: event.target.value })}
                    />
                    <span>{selected.font?.color ?? document.theme.colors.text}</span>
                  </span>
                </label>
              </div>
              <div className="format-controls" aria-label="Text formatting">
                <button
                  type="button"
                  aria-label="Bold"
                  aria-pressed={selected.font?.bold ?? false}
                  onClick={() => updateSelectedTextFont({ bold: !(selected.font?.bold ?? false) })}
                >B</button>
                <button
                  type="button"
                  className="is-italic"
                  aria-label="Italic"
                  aria-pressed={selected.font?.italic ?? false}
                  onClick={() => updateSelectedTextFont({ italic: !(selected.font?.italic ?? false) })}
                >I</button>
                <select
                  aria-label="Text alignment"
                  value={selected.horizontalAlign}
                  onChange={(event) => updateElement({
                    ...selected,
                    horizontalAlign: event.target.value as "left" | "center" | "right",
                  })}
                >
                  <option value="left">Align left</option>
                  <option value="center">Align center</option>
                  <option value="right">Align right</option>
                </select>
              </div>
              <p>Drag or resize the selected element directly on the canvas.</p>
              {renderElementActions()}
            </div>
          ) : selected?.type === "image" ? (
            <div className="property-form">
              <label htmlFor="selected-image-fit">Image fit</label>
              <select
                id="selected-image-fit"
                value={selected.fit}
                onChange={(event) => updateSelectedImage({ fit: event.target.value as "contain" | "cover" | "fill" })}
              >
                <option value="cover">Cover frame</option>
                <option value="contain">Fit inside frame</option>
                <option value="fill">Stretch to frame</option>
              </select>
              <label htmlFor="selected-image-alt">Alt text</label>
              <textarea
                id="selected-image-alt"
                className="property-form__short-textarea"
                maxLength={1000}
                value={selected.alt}
                placeholder="Describe the image for accessibility"
                onChange={(event) => updateSelectedImage({ alt: event.target.value })}
              />
              <p>Drag, resize, or rotate the image directly on the canvas.</p>
              {renderElementActions()}
            </div>
          ) : selected?.type === "shape" ? (
            <div className="property-form">
              <label htmlFor="selected-shape-type">Shape</label>
              <select
                id="selected-shape-type"
                value={selected.shape}
                onChange={(event) => updateSelectedShape({
                  shape: event.target.value as "rectangle" | "ellipse" | "triangle" | "diamond",
                })}
              >
                <option value="rectangle">Rectangle</option>
                <option value="ellipse">Ellipse</option>
                <option value="triangle">Triangle</option>
                <option value="diamond">Diamond</option>
              </select>
              <div className="property-grid">
                <label>
                  <span>Fill</span>
                  <span className="color-field">
                    <input
                      aria-label="Shape fill color"
                      type="color"
                      value={selected.fill?.color ?? document.theme.colors.primary}
                      onChange={(event) => updateSelectedShape({
                        fill: { color: event.target.value, opacity: selected.fill?.opacity ?? 1 },
                      })}
                    />
                    <span>{selected.fill?.color ?? document.theme.colors.primary}</span>
                  </span>
                </label>
                <label>
                  <span>Corner</span>
                  <input
                    type="number"
                    min="0"
                    max="200"
                    disabled={selected.shape !== "rectangle"}
                    value={selected.cornerRadius}
                    onChange={(event) => {
                      const radius = Number(event.target.value);
                      if (Number.isFinite(radius)) updateSelectedShape({ cornerRadius: Math.min(200, Math.max(0, radius)) });
                    }}
                  />
                </label>
              </div>
              <p>Drag, resize, or rotate the shape directly on the canvas.</p>
              {renderElementActions()}
            </div>
          ) : (
            selected ? (
              <div className="property-form">
                <p>Drag, resize, or rotate the selected {selected.type} directly on the canvas.</p>
                {renderElementActions()}
              </div>
            ) : (
              <div className="selection-empty">
                <Sparkle size={22} />
                <h2>Select an element</h2>
                <p>Choose an element on the slide to inspect its properties.</p>
              </div>
            )
          )}
        </aside>
      </section>
      {actionError ? <p className="editor-notice" role="alert">{actionError}</p> : null}
      {presenting ? (
        <section className="present-mode" aria-label="Presentation mode" role="dialog" aria-modal="true">
          <div className="present-stage">
            <SlideCanvas
              elements={slide.elements}
              background={slide.background}
              selectedElementId={null}
              onSelectElement={() => undefined}
              onChangeElement={() => undefined}
              readOnly
              resolveAssetUrl={resolveAssetUrl}
            />
          </div>
          <div className="present-controls">
            <button
              className="present-control"
              aria-label="Previous slide"
              disabled={activeSlideIndex === 0}
              onClick={() => setActiveSlideIndex((current) => Math.max(0, current - 1))}
            ><CaretLeft size={20} /></button>
            <span>{activeSlideIndex + 1} / {document.slides.length}</span>
            <button
              className="present-control"
              aria-label="Next slide"
              disabled={activeSlideIndex === document.slides.length - 1}
              onClick={() => setActiveSlideIndex((current) => Math.min(document.slides.length - 1, current + 1))}
            ><CaretRight size={20} /></button>
          </div>
          <button className="present-close" aria-label="Exit presentation" onClick={() => setPresenting(false)}>
            <X size={20} />
          </button>
        </section>
      ) : null}
    </main>
  );
}
