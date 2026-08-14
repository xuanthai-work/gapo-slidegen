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

type ComposerMode = "prompt" | "manuscript" | "file";
type ThemeId = "modern-blue" | "editorial-cobalt" | "warm-studio" | "midnight-signal";

const themes: Array<{ id: ThemeId; name: string; colors: [string, string, string] }> = [
  { id: "modern-blue", name: "Modern Blue", colors: ["#FFFFFF", "#1E4CD9", "#F5F8FE"] },
  { id: "editorial-cobalt", name: "Editorial", colors: ["#172033", "#285FC7", "#E3AA45"] },
  { id: "warm-studio", name: "Warm Studio", colors: ["#2E2925", "#C45132", "#D9A441"] },
  { id: "midnight-signal", name: "Midnight", colors: ["#09111F", "#4F86F7", "#F4B860"] },
];

export function Dashboard() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [presentations, setPresentations] = useState<StoredPresentation[]>([]);
  const [startingSourceId, setStartingSourceId] = useState<string | null>(null);
  const [activeGenerationSource, setActiveGenerationSource] = useState<StoredSource | null>(null);
  const [mode, setMode] = useState<ComposerMode>("prompt");
  const [slideCount, setSlideCount] = useState(10);
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
  const fileInput = useRef<HTMLInputElement>(null);
  const pollTimer = useRef<number | null>(null);
  const pollingJobId = useRef<string | null>(null);

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
            trackJob(source.id, latest.id);
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
      await startGeneration(source, slideCount, themeId);
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
      await startGeneration(source, slideCount, themeId);
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

  async function pollJob(sourceId: string, jobId: string) {
    if (pollingJobId.current !== jobId) return;
    try {
      const job = await apiFetch<GenerationJob>(`/v1/jobs/${jobId}`);
      if (pollingJobId.current !== jobId) return;
      setJobs((current) => ({ ...current, [sourceId]: job }));
      if (job.status === "succeeded" && job.result?.presentation_id) {
        pollingJobId.current = null;
        window.location.assign(`/editor?presentation=${job.result.presentation_id}`);
        return;
      }
      if (job.status === "queued" || job.status === "running") {
        pollTimer.current = window.setTimeout(() => void pollJob(sourceId, jobId), 1000);
      } else {
        pollingJobId.current = null;
      }
    } catch (caught) {
      if (pollingJobId.current !== jobId) return;
      setError(caught instanceof ApiError ? caught.message : "Could not read generation progress.");
      pollTimer.current = window.setTimeout(() => void pollJob(sourceId, jobId), 2000);
    }
  }

  function trackJob(sourceId: string, jobId: string) {
    pollingJobId.current = jobId;
    if (pollTimer.current !== null) window.clearTimeout(pollTimer.current);
    void pollJob(sourceId, jobId);
  }

  async function startGeneration(
    source: StoredSource,
    requestedSlideCount = 10,
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
          slide_count: requestedSlideCount,
          language: navigator.language.toLowerCase().startsWith("vi") ? "vi" : "en",
          theme_id: requestedThemeId,
        }),
      });
      setJobs((current) => ({ ...current, [source.id]: job }));
      trackJob(source.id, job.id);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not start generation.");
    } finally {
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

  if (loading) {
    return <main className="dashboard-loading">Loading your workspace…</main>;
  }

  return (
    <main className="dashboard-shell">
      <header className="dashboard-topbar">
        <a className="dashboard-brand" href="/">
          <span className="dashboard-brand__mark"><MagicWand size={18} weight="fill" /></span>
          Gapo SlideGen
        </a>
        <div className="account-menu">
          <span>{user?.email}</span>
          <button className="icon-button" onClick={logout} aria-label="Sign out">
            <SignOut size={18} />
          </button>
        </div>
      </header>

      <div className="dashboard-content">
        <section className="dashboard-hero">
          <p className="eyebrow">Presentation workspace</p>
          <h1>What are we presenting?</h1>
          <p>Bring a rough idea or finished content. The source stays editable and owned by you.</p>
        </section>

        <section className="composer-card">
          <div className="composer-tabs" role="tablist" aria-label="Source type">
            <button className={mode === "prompt" ? "is-active" : ""} onClick={() => setMode("prompt")}>Prompt</button>
            <button className={mode === "manuscript" ? "is-active" : ""} onClick={() => setMode("manuscript")}>Full text</button>
            <button className={mode === "file" ? "is-active" : ""} onClick={() => setMode("file")}>Upload</button>
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
              <div className="composer-options composer-options--upload">
                <label className="slide-count-field">
                  <span>Slides</span>
                  <input type="number" min="1" max="30" value={slideCount} onChange={(event) => setSlideCount(Math.min(30, Math.max(1, Number(event.target.value) || 1)))} />
                </label>
              </div>
              <fieldset className="theme-picker theme-picker--upload">
                <legend>Visual theme</legend>
                <div>
                  {themes.map((theme) => (
                    <label className={themeId === theme.id ? "is-selected" : ""} key={theme.id}>
                      <input type="radio" name="upload-theme" value={theme.id} checked={themeId === theme.id} onChange={() => setThemeId(theme.id)} />
                      <span className="theme-swatches" aria-hidden="true">
                        {theme.colors.map((color) => <i style={{ background: color }} key={color} />)}
                      </span>
                      <span>{theme.name}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            </div>
          ) : (
            <form className="composer-form" onSubmit={createTextSource}>
              <input
                aria-label="Presentation title"
                placeholder="Presentation title (optional)"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={500}
              />
              <textarea
                aria-label={mode === "prompt" ? "Presentation prompt" : "Presentation content"}
                placeholder={
                  mode === "prompt"
                    ? "Describe the audience, goal, and key message…"
                    : "Paste the complete content you want organized into slides…"
                }
                value={text}
                onChange={(event) => setText(event.target.value)}
                required
              />
              <div className="composer-options">
                <label className="slide-count-field">
                  <span>Slides</span>
                  <input type="number" min="1" max="30" value={slideCount} onChange={(event) => setSlideCount(Math.min(30, Math.max(1, Number(event.target.value) || 1)))} />
                </label>
              </div>
              <fieldset className="theme-picker">
                <legend>Visual theme</legend>
                <div>
                  {themes.map((theme) => (
                    <label className={themeId === theme.id ? "is-selected" : ""} key={theme.id}>
                      <input type="radio" name="theme" value={theme.id} checked={themeId === theme.id} onChange={() => setThemeId(theme.id)} />
                      <span className="theme-swatches" aria-hidden="true">
                        {theme.colors.map((color) => <i style={{ background: color }} key={color} />)}
                      </span>
                      <span>{theme.name}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
              <div className="composer-actions">
                <span>You will go straight to the editable presentation.</span>
                <button className="button button--primary" type="submit" disabled={submitting || !text.trim()}>
                  <MagicWand size={17} /> {submitting ? "Working…" : "Generate presentation"}
                </button>
              </div>
            </form>
          )}
          {error ? <p className="dashboard-error" role="alert">{error}</p> : null}
        </section>

        {activeGenerationSource ? (
          <section className={`generation-banner${activeGenerationJob?.status === "failed" ? " generation-banner--failed" : ""}${activeGenerationJob?.status === "canceled" ? " generation-banner--canceled" : ""}`} aria-live="polite">
            <span className="generation-banner__icon"><MagicWand size={20} /></span>
            <div className="generation-banner__content">
              <strong>
                {activeGenerationJob?.status === "failed"
                  ? "Generation failed"
                  : activeGenerationJob?.status === "canceled"
                    ? "Generation canceled"
                    : `Building “${activeGenerationSource.title}”`}
              </strong>
              <p>
                {startingSourceId === activeGenerationSource.id || activeGenerationJob?.status === "queued"
                  ? "Queued — preparing your source…"
                  : activeGenerationJob?.status === "running"
                    ? `Creating the story and editable slides… ${activeGenerationJob.progress}%`
                    : activeGenerationJob?.status === "failed"
                      ? activeGenerationJob.error_message || "The presentation could not be generated."
                      : activeGenerationJob?.status === "canceled"
                        ? "No presentation was saved from this job."
                        : "Starting generation…"}
              </p>
              {activeGenerationJob?.status === "queued" || activeGenerationJob?.status === "running" ? (
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
              ) : null}
            </div>
            {activeGenerationJob?.status === "failed" || activeGenerationJob?.status === "canceled" ? (
              <button className="button" onClick={() => void startGeneration(activeGenerationSource, slideCount)}>Retry</button>
            ) : activeGenerationJob?.status === "queued" || activeGenerationJob?.status === "running" ? (
              <button
                className="button generation-cancel"
                disabled={cancelingJobId === activeGenerationJob.id}
                onClick={() => void cancelGeneration(activeGenerationSource.id, activeGenerationJob.id)}
              >
                {cancelingJobId === activeGenerationJob.id ? "Canceling…" : "Cancel"}
              </button>
            ) : <span className="generation-pulse" aria-hidden="true" />}
          </section>
        ) : null}

        <section className="presentation-section">
          <div className="section-heading">
            <div><p className="eyebrow">Your decks</p><h2>Recent presentations</h2></div>
            <span>{presentations.length} deck{presentations.length === 1 ? "" : "s"}</span>
          </div>
          {presentations.length === 0 ? (
            <div className="presentation-empty">
              Generated presentations will appear here so you can reopen and continue editing them.
            </div>
          ) : (
            <div className="presentation-strip">
              {presentations.map((presentation) => {
                const candidate = presentation.document as { slides?: unknown[] } | null;
                const count = Array.isArray(candidate?.slides) ? candidate.slides.length : 0;
                return (
                  <article className="presentation-item" key={presentation.id}>
                    {renamingPresentationId === presentation.id ? (
                      <form className="presentation-rename" onSubmit={(event) => void renamePresentation(event, presentation)}>
                        <label htmlFor={`rename-${presentation.id}`}>Presentation name</label>
                        <input
                          id={`rename-${presentation.id}`}
                          value={renameDraft}
                          maxLength={500}
                          autoFocus
                          onChange={(event) => setRenameDraft(event.target.value)}
                        />
                        <div>
                          <button className="button button--primary" type="submit" disabled={!renameDraft.trim() || presentationActionId === presentation.id}>
                            {presentationActionId === presentation.id ? "Saving…" : "Save"}
                          </button>
                          <button className="button" type="button" disabled={presentationActionId === presentation.id} onClick={() => setRenamingPresentationId(null)}>Cancel</button>
                        </div>
                      </form>
                    ) : (
                      <>
                        <a className="presentation-item__open" href={`/editor?presentation=${presentation.id}`}>
                          <span className="presentation-item__preview"><FilePpt size={24} /></span>
                          <span className="presentation-item__copy">
                            <strong>{presentation.title}</strong>
                            <small>{count} slide{count === 1 ? "" : "s"}</small>
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
