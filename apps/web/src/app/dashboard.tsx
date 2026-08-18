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
import { TemplateCard } from "./components/template-card";
import { ThemeToggle } from "./components/theme-toggle";

type ComposerMode = "prompt" | "manuscript" | "file";
type ThemeId = "modern-blue" | "editorial-cobalt" | "warm-studio" | "midnight-signal";

type ThemePalette = { paper: string; ink: string; accent: string };

const themes: Array<{ id: ThemeId; name: string; colors: ThemePalette }> = [
  {
    id: "modern-blue",
    name: "Modern Blue",
    colors: { paper: "#FFFFFF", ink: "#1E4CD9", accent: "#F5F8FE" },
  },
  {
    id: "editorial-cobalt",
    name: "Editorial",
    colors: { paper: "#172033", ink: "#285FC7", accent: "#E3AA45" },
  },
  {
    id: "warm-studio",
    name: "Warm Studio",
    colors: { paper: "#2E2925", ink: "#C45132", accent: "#D9A441" },
  },
  {
    id: "midnight-signal",
    name: "Midnight",
    colors: { paper: "#09111F", ink: "#4F86F7", accent: "#F4B860" },
  },
];

export function Dashboard() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [presentations, setPresentations] = useState<StoredPresentation[]>([]);
  const [startingSourceId, setStartingSourceId] = useState<string | null>(null);
  const [activeGenerationSource, setActiveGenerationSource] = useState<StoredSource | null>(null);
  const [mode, setMode] = useState<ComposerMode>("prompt");
  const [themeId, setThemeId] = useState<ThemeId>("modern-blue");
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
  const [streamSlides, setStreamSlides] = useState<Record<string, Array<{ index: number; title: string; role: string }>>>({});
  const fileInput = useRef<HTMLInputElement>(null);
  const pollTimer = useRef<number | null>(null);
  const pollingJobId = useRef<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

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

  useEffect(() => () => {
    pollingJobId.current = null;
    if (pollTimer.current !== null) window.clearTimeout(pollTimer.current);
  }, []);

  async function createTextSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
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
      await startGeneration(source, themeId);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not create the source.");
    } finally {
      setSubmitting(false);
    }
  }

  async function uploadFile(file: File) {
    setSubmitting(true);
    setError(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const source = await apiFetch<StoredSource>("/v1/sources/files", {
        method: "POST",
        body,
      });
      await startGeneration(source, themeId);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not upload the document.");
    } finally {
      setSubmitting(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function logout() {
    await apiFetch<void>("/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    window.location.replace("/login");
  }

  function closeEventStream() {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }

  function trackJob(sourceId: string, jobId: string) {
    pollingJobId.current = jobId;
    if (pollTimer.current !== null) window.clearTimeout(pollTimer.current);
    closeEventStream();

    const url = `/api/jobs/${jobId}/events`;
    console.log("[SSE] connecting", url);
    const source = new EventSource(url);
    eventSourceRef.current = source;

    source.addEventListener("open", () => {
      console.log("[SSE] open", jobId);
    });

    source.addEventListener("progress", (event) => {
      console.log("[SSE] progress", event.data);
      if (pollingJobId.current !== jobId) {
        closeEventStream();
        return;
      }
      try {
        const job = JSON.parse(event.data) as GenerationJob;
        setJobs((current) => ({ ...current, [sourceId]: job }));
        if (job.status === "succeeded" && job.result?.presentation_id) {
          pollingJobId.current = null;
          closeEventStream();
          window.location.assign(`/editor?presentation=${job.result.presentation_id}`);
          return;
        }
        if (job.status === "failed" || job.status === "canceled") {
          pollingJobId.current = null;
          closeEventStream();
        }
      } catch {
        // Ignore malformed SSE payload and let the connection continue.
      }
    });

    source.addEventListener("slide", (event) => {
      console.log("[SSE] slide", event.data);
      if (pollingJobId.current !== jobId) {
        closeEventStream();
        return;
      }
      try {
        const payload = JSON.parse(event.data) as {
          stage: string;
          message: string;
          slide_count: number;
          latest_slide: Record<string, unknown> | null;
          slides: Array<Record<string, unknown>>;
        };
        const slides = payload.slides.map((slide, index) => {
          const preview = extractSlidePreview(slide);
          return { index, ...preview };
        });
        setStreamSlides((current) => ({ ...current, [sourceId]: slides }));
      } catch {
        // Ignore malformed slide payload.
      }
    });

    source.addEventListener("error", (event) => {
      console.log("[SSE] error", event);
      if (pollingJobId.current !== jobId) {
        closeEventStream();
        return;
      }
      // Fall back to one-time fetch on SSE errors, then retry SSE after a short delay.
      closeEventStream();
      void apiFetch<GenerationJob>(`/v1/jobs/${jobId}`)
        .then((job) => {
          setJobs((current) => ({ ...current, [sourceId]: job }));
          if (job.status === "succeeded" && job.result?.presentation_id) {
            pollingJobId.current = null;
            window.location.assign(`/editor?presentation=${job.result.presentation_id}`);
          } else if (job.status === "queued" || job.status === "running") {
            pollTimer.current = window.setTimeout(() => trackJob(sourceId, jobId), 2000);
          } else {
            pollingJobId.current = null;
          }
        })
        .catch((caught: unknown) => {
          if (pollingJobId.current !== jobId) return;
          setError(caught instanceof ApiError ? caught.message : "Could not read generation progress.");
          pollTimer.current = window.setTimeout(() => trackJob(sourceId, jobId), 2000);
        });
    });
  }

  async function startGeneration(
    source: StoredSource,
    requestedThemeId: ThemeId = themeId,
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
          theme_id: requestedThemeId,
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
      pollingJobId.current = null;
      if (pollTimer.current !== null) window.clearTimeout(pollTimer.current);
      closeEventStream();
      setJobs((current) => ({ ...current, [sourceId]: job }));
      setStreamSlides((current) => {
        const next = { ...current };
        delete next[sourceId];
        return next;
      });
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

function extractSlidePreview(slide: Record<string, unknown>): { title: string; role: string } {
  let title = "";
  if (typeof slide.title === "string" && slide.title.trim()) {
    title = slide.title;
  } else {
    const elements = Array.isArray(slide.elements) ? slide.elements : [];
    for (const element of elements) {
      if (typeof element === "object" && element !== null) {
        const el = element as Record<string, unknown>;
        const runs = Array.isArray(el.runs) ? el.runs : [];
        for (const run of runs) {
          if (typeof run === "object" && run !== null && typeof (run as Record<string, unknown>).text === "string") {
            const text = (run as Record<string, unknown>).text as string;
            if (text.trim()) {
              title = text.trim();
              break;
            }
          }
        }
        if (title) break;
      }
    }
  }
  const role = typeof slide.role === "string" ? slide.role : "";
  return { title: title || "Slide", role };
}

function TypingSlidePreview({
  number,
  title,
  role,
  isActive,
}: {
  number: number;
  title: string;
  role: string;
  isActive: boolean;
}) {
  const [displayed, setDisplayed] = useState(isActive ? "" : title);
  const [showCursor, setShowCursor] = useState(isActive);

  useEffect(() => {
    if (!isActive) {
      setDisplayed(title);
      setShowCursor(false);
      return;
    }
    setDisplayed("");
    setShowCursor(true);
    let index = 0;
    const interval = window.setInterval(() => {
      index += 1;
      setDisplayed(title.slice(0, index));
      if (index >= title.length) {
        window.clearInterval(interval);
        setShowCursor(false);
      }
    }, 45);
    return () => window.clearInterval(interval);
  }, [isActive, title]);

  return (
    <li className="generation-stream__slide">
      <span className="generation-stream__number">{number}</span>
      <div className="generation-stream__copy" style={{ minWidth: 0 }}>
        <span className="generation-stream__title">
          {displayed}
          {showCursor ? <span className="generation-cursor" /> : null}
        </span>
        {role ? <span className="generation-stream__role">{role}</span> : null}
      </div>
    </li>
  );
}

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
                  if (file) void uploadFile(file);
                }}
              />
              <label className="button button--primary" htmlFor="source-file">
                <UploadSimple size={17} /> {submitting ? "Working…" : "Choose file & generate"}
              </label>
              <fieldset className="template-picker" aria-label="Visual theme">
                <legend className="template-picker__legend">Visual theme</legend>
                <div className="template-picker__grid">
                  {themes.map((theme) => (
                    <TemplateCard
                      key={theme.id}
                      id={theme.id}
                      name={theme.name}
                      colors={theme.colors}
                      selected={themeId === theme.id}
                      onSelect={(id) => setThemeId(id as ThemeId)}
                    />
                  ))}
                </div>
              </fieldset>
            </div>
          ) : (
            <form className="composer-form" onSubmit={createTextSource}>
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
              <fieldset className="template-picker" aria-label="Visual theme">
                <legend className="template-picker__legend">Visual theme</legend>
                <div className="template-picker__grid">
                  {themes.map((theme) => (
                    <TemplateCard
                      key={theme.id}
                      id={theme.id}
                      name={theme.name}
                      colors={theme.colors}
                      selected={themeId === theme.id}
                      onSelect={(id) => setThemeId(id as ThemeId)}
                    />
                  ))}
                </div>
              </fieldset>
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
            className={`generation-banner${
              activeGenerationJob?.status === "failed" ? " generation-banner--failed" : ""
            }${
              activeGenerationJob?.status === "canceled" ? " generation-banner--canceled" : ""
            }`}
            aria-live="polite"
          >
            <span className="generation-banner__icon">
              <MagicWand size={20} />
            </span>
            <div className="generation-banner__content">
              <p className="generation-banner__eyebrow">
                {activeGenerationJob?.status === "failed"
                  ? "Generation failed"
                  : activeGenerationJob?.status === "canceled"
                    ? "Generation canceled"
                    : "Building presentation"}
              </p>
              <strong className="generation-banner__heading">
                {activeGenerationJob?.status === "running" || activeGenerationJob?.status === "queued"
                  ? `“${activeGenerationSource.title}”`
                  : activeGenerationJob?.status === "failed" || activeGenerationJob?.status === "canceled"
                    ? activeGenerationSource.title
                    : `“${activeGenerationSource.title}”`}
              </strong>
              <p className="generation-banner__body">
                {(() => {
                  if (!activeGenerationSource) return "Starting generation…";
                  const previewSlides = streamSlides[activeGenerationSource.id];
                  const hasSlides = activeGenerationJob?.status === "running" && previewSlides && previewSlides.length > 0;
                  if (startingSourceId === activeGenerationSource.id || activeGenerationJob?.status === "queued") {
                    return "Queued — preparing your source…";
                  }
                  if (activeGenerationJob?.status === "running") {
                    return hasSlides ? `Building ${previewSlides.length} slides…` : "Planning the story…";
                  }
                  if (activeGenerationJob?.status === "failed") {
                    return activeGenerationJob.error_message || "The presentation could not be generated.";
                  }
                  if (activeGenerationJob?.status === "canceled") {
                    return "No presentation was saved from this job.";
                  }
                  return "Starting generation…";
                })()}
              </p>
              {(() => {
                if (!activeGenerationSource || activeGenerationJob?.status !== "running") return null;
                const previewSlides = streamSlides[activeGenerationSource.id];
                if (previewSlides && previewSlides.length > 0) {
                  return (
                    <ol className="generation-stream" aria-live="polite" aria-label="Generated slides preview">
                      {previewSlides.map((slide, listIndex) => (
                        <TypingSlidePreview
                          key={slide.index}
                          number={slide.index + 1}
                          title={slide.title}
                          role={slide.role}
                          isActive={listIndex === previewSlides.length - 1}
                        />
                      ))}
                    </ol>
                  );
                }
                return (
                  <div
                    className="generation-progress"
                    role="progressbar"
                    aria-label="Presentation generation progress"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={activeGenerationJob.progress}
                  >
                    <span style={{ width: `${activeGenerationJob.progress}%` }} />
                  </div>
                );
              })()}
            </div>
            {activeGenerationJob?.status === "failed" || activeGenerationJob?.status === "canceled" ? (
              <button className="button" onClick={() => void startGeneration(activeGenerationSource)}>
                Retry
              </button>
            ) : activeGenerationJob?.status === "queued" || activeGenerationJob?.status === "running" ? (
              <button
                className="button generation-cancel"
                disabled={cancelingJobId === activeGenerationJob.id}
                onClick={() =>
                  void cancelGeneration(activeGenerationSource.id, activeGenerationJob.id)
                }
              >
                {cancelingJobId === activeGenerationJob.id ? "Canceling…" : "Cancel"}
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
    </main>
  );
}
