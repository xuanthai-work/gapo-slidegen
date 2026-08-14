"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowLeft, DownloadSimple, Play, Sparkle } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
import { EditorBoundary } from "@gapo-slidegen/slide-editor";
import { canonicalPresentationFixture } from "@gapo-slidegen/slide-schema/fixtures";
import { parsePresentation, type Presentation, type SlideElement } from "@gapo-slidegen/slide-schema";
import { ApiError, apiFetch, type StoredPresentation } from "../lib/api";

const SlideCanvas = dynamic(() => import("./editor-canvas"), { ssr: false });

export function EditorSpike({ presentationId }: { presentationId: string | undefined }) {
  const [initialDocument, setInitialDocument] = useState<Presentation>(() =>
    structuredClone(canonicalPresentationFixture),
  );
  const [document, setDocument] = useState<Presentation>(() =>
    structuredClone(canonicalPresentationFixture),
  );
  const [selectedElementId, setSelectedElementId] = useState<string | null>("title");
  const [loadError, setLoadError] = useState<string | null>(null);
  const editor = useMemo(
    () =>
      new EditorBoundary({
        initialDocument,
        onChange: ({ document: nextDocument }) => setDocument(nextDocument),
      }),
    [initialDocument],
  );
  const slide = document.slides[0];
  const selected = slide?.elements.find((element) => element.id === selectedElementId);

  useEffect(() => {
    if (!presentationId) return;
    apiFetch<StoredPresentation>(`/v1/presentations/${presentationId}`)
      .then((stored) => {
        const parsed = parsePresentation(stored.document);
        setInitialDocument(parsed);
        setDocument(parsed);
        setSelectedElementId(parsed.slides[0]?.elements[0]?.id ?? null);
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 401) {
          window.location.replace("/login");
          return;
        }
        setLoadError(caught instanceof Error ? caught.message : "Could not load presentation.");
      });
  }, [presentationId]);

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
    updateElement({ ...selected, runs: [{ text: value }] });
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
          <span className="document-title">{document.title}</span>
          <span className="save-state">Saved locally</span>
        </div>
        <div className="topbar__actions">
          <button className="button button--quiet"><Play size={17} />Present</button>
          <button className="button button--primary"><DownloadSimple size={17} />Export</button>
        </div>
      </header>

      <section className="editor-grid">
        <aside className="filmstrip" aria-label="Slides">
          <h2>Slides</h2>
          <button className="thumbnail thumbnail--active" aria-label="Slide 1">
            <span className="thumbnail__number">1</span>
            <span className="thumbnail__preview">Quarterly<br />product review</span>
          </button>
          <button className="add-slide">+ Add slide</button>
        </aside>

        <section className="workspace" aria-label="Slide canvas">
          <div className="insert-bar">
            <button>Insert</button><button>Text</button><button>Shape</button><button>Image</button>
          </div>
          <div className="canvas-frame">
            <SlideCanvas
              elements={slide.elements}
              background={slide.background}
              selectedElementId={selectedElementId}
              onSelectElement={setSelectedElementId}
              onChangeElement={updateElement}
            />
          </div>
          <div className="zoom-control">Fit to workspace</div>
        </section>

        <aside className="properties">
          <div className="panel-tabs"><button className="is-active">Properties</button><button>AI</button></div>
          {selected?.type === "text" ? (
            <div className="property-form">
              <label htmlFor="selected-text">Text</label>
              <textarea
                id="selected-text"
                value={selected.runs.map((run) => run.text).join("")}
                onChange={(event) => updateSelectedText(event.target.value)}
              />
              <p>Drag or resize the selected element directly on the canvas.</p>
            </div>
          ) : (
            <div className="selection-empty">
              <Sparkle size={22} />
              <h2>Select an element</h2>
              <p>Choose an element on the slide to inspect its properties.</p>
            </div>
          )}
        </aside>
      </section>
    </main>
  );
}
