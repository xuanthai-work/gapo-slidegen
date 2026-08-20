"use client";

import {
  ArrowRight,
  FilePpt,
  MagicWand,
  PencilSimple,
  SignOut,
  Trash,
  UploadSimple,
} from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  ApiError,
  apiFetch,
  type CurrentUser,
  type GenerationJob,
  type StoredPresentation,
  type StoredSource,
} from "../lib/api";
import { EmptyState } from "./components/empty-state";
import { LandingHero } from "./components/landing-hero";
import { Skeleton } from "./components/skeleton";
import { ThemeHud, type ThemeHudSelection } from "./components/theme-hud";
import { ThemeToggle } from "./components/theme-toggle";

type ComposerMode = "prompt" | "manuscript" | "file";
type PendingGeneration =
  | { kind: "text" }
  | { kind: "file"; file: File }
  | { kind: "retry"; source: StoredSource };

export function Dashboard() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [presentations, setPresentations] = useState<StoredPresentation[]>([]);
  const [startingSourceId, setStartingSourceId] = useState<string | null>(null);
  const [activeGenerationSource, setActiveGenerationSource] = useState<StoredSource | null>(null);
  const [mode, setMode] = useState<ComposerMode>("prompt");
  const [hudOpen, setHudOpen] = useState(false);
  const [pendingGeneration, setPendingGeneration] = useState<PendingGeneration | null>(null);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [cancelingJobId, setCancelingJobId] = useState<string | null>(null);
  const [renamingPresentationId, setRenamingPresentationId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [presentationActionId, setPresentationActionId] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Record<string, GenerationJob>>({});
  const fileInput = useRef<HTMLInputElement>(null);

  async function runSubmission(
    task: () => Promise<void>,
    fallbackError: string,
    onFinally?: () => void,
  ) {
    setSubmitting(true);
    setError(null);
    try {
      await task();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : fallbackError);
    } finally {
      setSubmitting(false);
      onFinally?.();
    }
  }

  useEffect(() => {
    Promise.all([
      apiFetch<CurrentUser>("/v1/auth/me"),
      apiFetch<StoredPresentation[]>("/v1/presentations"),
      apiFetch<GenerationJob[]>("/v1/jobs?limit=20"),
    ])
      .then(async ([currentUser, currentPresentations, recentJobs]) => {
        setUser(currentUser);
        setPresentations(currentPresentations);
        const latestActive = recentJobs.find(
          (job) => job.status === "queued" || job.status === "running",
        );
        const latest = latestActive
          ?? (["failed", "canceled"].includes(recentJobs[0]?.status ?? "") ? recentJobs[0] : undefined);
        if (
          !latest?.source_id
          || !["queued", "running", "failed", "canceled"].includes(latest.status)
        ) return;
        try {
          const source = await apiFetch<StoredSource>(`/v1/sources/${latest.source_id}`);
          setActiveGenerationSource(source);
          setJobs((current) => ({ ...current, [source.id]: latest }));
          if (latest.status === "queued" || latest.status === "running") {
            window.location.assign(`/editor?job=${latest.id}`);
            return;
          }
        } catch {
          // Expired terminal-job sources are intentionally omitted from recovery.
        }
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 401) {
          window.location.replace("/login");
          return;
        }
        setError("The API is unavailable. Confirm FastAPI and PostgreSQL are running.");
      })
      .finally(() => setLoading(false));
  }, []);

  function openThemeHud(pending: PendingGeneration) {
    setError(null);
    setPendingGeneration(pending);
    setHudOpen(true);
  }

  function closeThemeHud() {
    setHudOpen(false);
    setPendingGeneration(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  function requestTextGeneration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!text.trim()) return;
    openThemeHud({ kind: "text" });
  }

  async function createTextSource(selection: ThemeHudSelection) {
    await runSubmission(async () => {
      const source = await apiFetch<StoredSource>("/v1/sources/text", {
        method: "POST",
        body: JSON.stringify({
          kind: mode,
          title: title || (mode === "prompt" ? "New presentation" : "Untitled manuscript"),
          text,
        }),
      });
      setTitle("");
      setText("");
      await startGeneration(source, selection);
    }, "Could not create the source.");
  }

  async function uploadFile(file: File, selection: ThemeHudSelection) {
    await runSubmission(async () => {
      const body = new FormData();
      body.append("file", file);
      const source = await apiFetch<StoredSource>("/v1/sources/files", {
        method: "POST",
        body,
      });
      await startGeneration(source, selection);
    }, "Could not upload the document.", () => {
      if (fileInput.current) fileInput.current.value = "";
    });
  }

  async function confirmThemeHud(selection: ThemeHudSelection) {
    const pending = pendingGeneration;
    setHudOpen(false);
    setPendingGeneration(null);
    if (pending?.kind === "file") {
      await uploadFile(pending.file, selection);
      return;
    }
    if (pending?.kind === "retry") {
      await startGeneration(pending.source, selection);
      return;
    }
    if (pending?.kind === "text") {
      await createTextSource(selection);
    }
  }

  async function logout() {
    await apiFetch<void>("/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    window.location.replace("/login");
  }

  async function startGeneration(
    source: StoredSource,
    selection: ThemeHudSelection,
  ) {
    setError(null);
    setStartingSourceId(source.id);
    setActiveGenerationSource(source);
    try {
      const job = await apiFetch<GenerationJob>("/v1/generations", {
        method: "POST",
        body: JSON.stringify({
          source_id: source.id,
          language: navigator.language.toLowerCase().startsWith("vi") ? "vi" : "en",
          template_id: selection.templateId,
          color_scheme_id: selection.colorSchemeId,
        }),
      });
      console.log("[SSE] generation started", job.id, job.status);
      window.location.assign(`/editor?job=${job.id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not start generation.");
      setStartingSourceId(null);
    }
  }

  async function cancelGeneration(sourceId: string, jobId: string) {
    setCancelingJobId(jobId);
    setError(null);
    try {
      const job = await apiFetch<GenerationJob>(`/v1/jobs/${jobId}/cancel`, {
        method: "POST",
      });
      setJobs((current) => ({ ...current, [sourceId]: job }));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not cancel generation.");
    } finally {
      setCancelingJobId(null);
    }
  }

  async function renamePresentation(
    event: FormEvent<HTMLFormElement>,
    presentation: StoredPresentation,
  ) {
    event.preventDefault();
    const nextTitle = renameDraft.trim();
    if (!nextTitle) return;
    setPresentationActionId(presentation.id);
    setError(null);
    try {
      const renamed = await apiFetch<StoredPresentation>(
        `/v1/presentations/${presentation.id}/title`,
        {
          method: "PATCH",
          body: JSON.stringify({
            expected_revision: presentation.revision,
            title: nextTitle,
          }),
        },
      );
      setPresentations((current) => current.map((item) => (
        item.id === renamed.id ? renamed : item
      )));
      setRenamingPresentationId(null);
      setRenameDraft("");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not rename the presentation.");
    } finally {
      setPresentationActionId(null);
    }
  }

  async function deletePresentation(presentation: StoredPresentation) {
    if (!window.confirm(`Delete “${presentation.title}”? This cannot be undone.`)) return;
    setPresentationActionId(presentation.id);
    setError(null);
    try {
      await apiFetch<void>(
        `/v1/presentations/${presentation.id}?expected_revision=${presentation.revision}`,
        { method: "DELETE" },
      );
      setPresentations((current) => current.filter((item) => item.id !== presentation.id));
      if (renamingPresentationId === presentation.id) {
        setRenamingPresentationId(null);
        setRenameDraft("");
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not delete the presentation.");
    } finally {
      setPresentationActionId(null);
    }
  }

  const activeGenerationJob = activeGenerationSource ? jobs[activeGenerationSource.id] : undefined;
  const activeGenerationStatus = activeGenerationJob?.status;
  const activeGenerationJobId = activeGenerationJob?.id ?? "";
  const generationBannerEyebrow = activeGenerationStatus === "failed"
    ? "Generation failed"
    : activeGenerationStatus === "canceled"
      ? "Generation canceled"
      : "Building presentation";
  const generationBannerHeading = activeGenerationStatus === "failed"
    || activeGenerationStatus === "canceled"
    ? activeGenerationSource?.title ?? ""
    : activeGenerationSource ? `“${activeGenerationSource.title}”` : "";
  const generationBannerBody = (() => {
    if (!activeGenerationSource) return "Starting generation…";
    if (startingSourceId === activeGenerationSource.id || activeGenerationStatus === "queued") {
      return "Queued — preparing your source…";
    }
    if (activeGenerationStatus === "running") {
      return "Planning the story…";
    }
    if (activeGenerationStatus === "failed") {
      return activeGenerationJob?.error_message || "The presentation could not be generated.";
    }
    if (activeGenerationStatus === "canceled") {
      return "No presentation was saved from this job.";
    }
    return "Starting generation…";
  })();
  const generationBannerClassName = `generation-banner${
    activeGenerationStatus === "failed" ? " generation-banner--failed" : ""
  }${
    activeGenerationStatus === "canceled" ? " generation-banner--canceled" : ""
  }`;

  if (loading) {
    return (
      <main className="dashboard-shell">
        <header className="dashboard-topbar">
          <a className="dashboard-brand" href="/">
            <span className="dashboard-brand__mark"><MagicWand size={18} weight="fill" /></span>
            <span className="dashboard-brand__wordmark">Gapo SlideGen</span>
          </a>
        </header>
        <div className="dashboard-content">
          <div className="dashboard-hero">
            <Skeleton width="120px" height="11px" />
            <div style={{ height: "var(--space-3)" }} />
            <Skeleton width="60%" height="56px" />
            <div style={{ height: "var(--space-3)" }} />
            <Skeleton width="80%" height="16px" />
          </div>
          <Skeleton width="100%" height="320px" radius="var(--radius-lg)" />
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard-shell">
      <a className="u-skip-link" href="#dashboard-content">Skip to main content</a>

      <header className="dashboard-topbar">
        <a className="dashboard-brand" href="/">
          <span className="dashboard-brand__mark"><MagicWand size={18} weight="fill" /></span>
          <span className="dashboard-brand__wordmark">Gapo SlideGen</span>
        </a>
        <div className="account-menu">
          <span>{user?.email}</span>
          <ThemeToggle />
          <button className="icon-button" onClick={logout} aria-label="Sign out">
            <SignOut size={18} />
          </button>
        </div>
      </header>

      <div id="dashboard-content" className="dashboard-content">
        <LandingHero
          eyebrow="Presentation workspace"
          heading="What are we presenting?"
          body="Bring a rough idea or finished content. The source stays editable and owned by you."
        />

        <section className="composer-card">
          <div className="composer-tabs" role="tablist" aria-label="Source type">
            <button
              className={mode === "prompt" ? "is-active" : ""}
              role="tab"
              aria-selected={mode === "prompt"}
              onClick={() => setMode("prompt")}
            >
              Prompt
            </button>
            <button
              className={mode === "manuscript" ? "is-active" : ""}
              role="tab"
              aria-selected={mode === "manuscript"}
              onClick={() => setMode("manuscript")}
            >
              Full text
            </button>
            <button
              className={mode === "file" ? "is-active" : ""}
              role="tab"
              aria-selected={mode === "file"}
              onClick={() => setMode("file")}
            >
              Upload
            </button>
          </div>

          {mode === "file" ? (
            <div className="upload-panel">
              <div className="upload-panel__icon"><UploadSimple size={25} /></div>
              <h2>Upload an existing document</h2>
              <p>DOCX, PPTX, or text-based PDF · maximum 25 MB</p>
              <input
                ref={fileInput}
                className="visually-hidden"
                id="source-file"
                type="file"
                accept=".docx,.pptx,.pdf"
                disabled={submitting}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) openThemeHud({ kind: "file", file });
                }}
              />
              <label className="button button--primary" htmlFor="source-file">
                <UploadSimple size={17} /> {submitting ? "Working…" : "Choose file"}
              </label>
            </div>
          ) : (
            <form className="composer-form" onSubmit={requestTextGeneration}>
              <label htmlFor="composer-title" className="composer-form__label">
                Presentation title <span className="composer-form__hint">(optional)</span>
              </label>
              <input
                id="composer-title"
                placeholder="A concise, memorable title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={500}
              />
              <label htmlFor="composer-text" className="composer-form__label">
                {mode === "prompt" ? "Prompt" : "Source text"}
              </label>
              <textarea
                id="composer-text"
                placeholder={
                  mode === "prompt"
                    ? "Describe the audience, goal, and key message…"
                    : "Paste the complete content you want organized into slides…"
                }
                value={text}
                onChange={(event) => setText(event.target.value)}
                required
              />
              <div className="composer-actions">
                <span>You will go straight to the editable presentation.</span>
                <button
                  className="button button--primary"
                  type="submit"
                  disabled={submitting || !text.trim()}
                >
                  <MagicWand size={17} /> {submitting ? "Working…" : "Generate presentation"}
                </button>
              </div>
            </form>
          )}
          {error ? <p className="dashboard-error" role="alert">{error}</p> : null}
        </section>

        {activeGenerationSource ? (
          <section
            className={generationBannerClassName}
            aria-live="polite"
          >
            <span className="generation-banner__icon">
              <MagicWand size={20} />
            </span>
            <div className="generation-banner__content">
              <p className="generation-banner__eyebrow">{generationBannerEyebrow}</p>
              <strong className="generation-banner__heading">{generationBannerHeading}</strong>
              <p className="generation-banner__body">{generationBannerBody}</p>
              {activeGenerationStatus === "running" ? (
                <div
                  className="generation-progress"
                  role="progressbar"
                  aria-label="Presentation generation progress"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={activeGenerationJob?.progress ?? 0}
                >
                  <span style={{ width: `${activeGenerationJob?.progress ?? 0}%` }} />
                </div>
              ) : null}
            </div>
            {activeGenerationStatus === "failed" || activeGenerationStatus === "canceled" ? (
              <button
                className="button"
                onClick={() => openThemeHud({ kind: "retry", source: activeGenerationSource })}
              >
                Retry
              </button>
            ) : activeGenerationStatus === "queued" || activeGenerationStatus === "running" ? (
              <button
                className="button generation-cancel"
                disabled={!activeGenerationJobId || cancelingJobId === activeGenerationJobId}
                onClick={() =>
                  activeGenerationJobId
                    ? void cancelGeneration(activeGenerationSource.id, activeGenerationJobId)
                    : undefined
                }
              >
                {cancelingJobId === activeGenerationJobId ? "Canceling…" : "Cancel"}
              </button>
            ) : (
              <span className="generation-pulse" aria-hidden="true" />
            )}
          </section>
        ) : null}

        <section className="presentation-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Your decks</p>
              <h2 className="section-heading__title">Recent presentations</h2>
            </div>
            <span className="section-heading__count">
              {presentations.length} deck{presentations.length === 1 ? "" : "s"}
            </span>
          </div>
          {presentations.length === 0 ? (
            <EmptyState
              icon={<FilePpt size={22} weight="duotone" />}
              eyebrow="Your decks"
              heading="No presentations yet"
              body="Generated presentations will appear here so you can reopen and continue editing them."
            />
          ) : (
            <div className="presentation-strip">
              {presentations.map((presentation) => {
                const candidate = presentation.document as { slides?: unknown[] } | null;
                const count = Array.isArray(candidate?.slides) ? candidate.slides.length : 0;
                return (
                  <article className="presentation-item u-lift" key={presentation.id}>
                    {renamingPresentationId === presentation.id ? (
                      <form
                        className="presentation-rename"
                        onSubmit={(event) => void renamePresentation(event, presentation)}
                      >
                        <label htmlFor={`rename-${presentation.id}`}>Presentation name</label>
                        <input
                          id={`rename-${presentation.id}`}
                          value={renameDraft}
                          maxLength={500}
                          autoFocus
                          onChange={(event) => setRenameDraft(event.target.value)}
                        />
                        <div>
                          <button
                            className="button button--primary"
                            type="submit"
                            disabled={!renameDraft.trim() || presentationActionId === presentation.id}
                          >
                            {presentationActionId === presentation.id ? "Saving…" : "Save"}
                          </button>
                          <button
                            className="button"
                            type="button"
                            disabled={presentationActionId === presentation.id}
                            onClick={() => setRenamingPresentationId(null)}
                          >
                            Cancel
                          </button>
                        </div>
                      </form>
                    ) : (
                      <>
                        <a
                          className="presentation-item__open"
                          href={`/editor?presentation=${presentation.id}`}
                        >
                          <span className="presentation-item__preview">
                            <FilePpt size={24} />
                          </span>
                          <span className="presentation-item__copy">
                            <strong>{presentation.title}</strong>
                            <small className="presentation-item__count">
                              <span className="presentation-item__count-number">{count}</span> slide{count === 1 ? "" : "s"}
                            </small>
                          </span>
                          <ArrowRight size={16} />
                        </a>
                        <div className="presentation-item__actions">
                          <button
                            type="button"
                            aria-label={`Rename ${presentation.title}`}
                            title="Rename"
                            disabled={presentationActionId === presentation.id}
                            onClick={() => {
                              setRenamingPresentationId(presentation.id);
                              setRenameDraft(presentation.title);
                            }}
                          >
                            <PencilSimple size={15} />
                          </button>
                          <button
                            type="button"
                            aria-label={`Delete ${presentation.title}`}
                            title="Delete"
                            disabled={presentationActionId === presentation.id}
                            onClick={() => void deletePresentation(presentation)}
                          >
                            <Trash size={15} />
                          </button>
                        </div>
                      </>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </div>
      <ThemeHud
        open={hudOpen}
        submitting={submitting}
        onCancel={closeThemeHud}
        onConfirm={(selection) => void confirmThemeHud(selection)}
      />
    </main>
  );
}
