"use client";

import {
  ArrowRight,
  FileDoc,
  FilePdf,
  FilePpt,
  MagicWand,
  Plus,
  SignOut,
  UploadSimple,
} from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  ApiError,
  apiFetch,
  type CurrentUser,
  type GenerationJob,
  type StoredSource,
} from "../lib/api";

type ComposerMode = "prompt" | "manuscript" | "file";

function sourceIcon(kind: StoredSource["kind"]) {
  if (kind === "pdf") return <FilePdf size={20} />;
  if (kind === "pptx") return <FilePpt size={20} />;
  if (kind === "docx") return <FileDoc size={20} />;
  return <MagicWand size={20} />;
}

export function Dashboard() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [sources, setSources] = useState<StoredSource[]>([]);
  const [mode, setMode] = useState<ComposerMode>("prompt");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [jobs, setJobs] = useState<Record<string, GenerationJob>>({});
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([
      apiFetch<CurrentUser>("/v1/auth/me"),
      apiFetch<StoredSource[]>("/v1/sources"),
    ])
      .then(([currentUser, currentSources]) => {
        setUser(currentUser);
        setSources(currentSources);
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
      setSources((current) => [source, ...current]);
      setTitle("");
      setText("");
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
      setSources((current) => [source, ...current]);
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
    try {
      const job = await apiFetch<GenerationJob>(`/v1/jobs/${jobId}`);
      setJobs((current) => ({ ...current, [sourceId]: job }));
      if (job.status === "succeeded" && job.result?.presentation_id) {
        window.location.assign(`/editor?presentation=${job.result.presentation_id}`);
        return;
      }
      if (job.status === "queued" || job.status === "running") {
        window.setTimeout(() => void pollJob(sourceId, jobId), 1000);
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not read generation progress.");
    }
  }

  async function generate(source: StoredSource) {
    setError(null);
    try {
      const job = await apiFetch<GenerationJob>("/v1/generations", {
        method: "POST",
        body: JSON.stringify({
          source_id: source.id,
          slide_count: 10,
          language: navigator.language.toLowerCase().startsWith("vi") ? "vi" : "en",
        }),
      });
      setJobs((current) => ({ ...current, [source.id]: job }));
      void pollJob(source.id, job.id);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not start generation.");
    }
  }

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
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void uploadFile(file);
                }}
              />
              <label className="button button--primary" htmlFor="source-file">
                <UploadSimple size={17} /> {submitting ? "Uploading…" : "Choose a file"}
              </label>
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
              <div className="composer-actions">
                <span>{mode === "prompt" ? "The AI generation step will use this context." : "Headings will guide the slide outline."}</span>
                <button className="button button--primary" type="submit" disabled={submitting || !text.trim()}>
                  <Plus size={17} /> {submitting ? "Saving…" : "Save source"}
                </button>
              </div>
            </form>
          )}
          {error ? <p className="dashboard-error" role="alert">{error}</p> : null}
        </section>

        <section className="source-section">
          <div className="section-heading">
            <div><p className="eyebrow">Your content</p><h2>Recent sources</h2></div>
            <span>{sources.length} item{sources.length === 1 ? "" : "s"}</span>
          </div>
          {sources.length === 0 ? (
            <div className="source-empty">
              <MagicWand size={24} />
              <h3>No sources yet</h3>
              <p>Save a prompt, paste your content, or upload a document to begin.</p>
            </div>
          ) : (
            <div className="source-list">
              {sources.map((source) => (
                <article className="source-row" key={source.id}>
                  <div className="source-row__icon">{sourceIcon(source.kind)}</div>
                  <div className="source-row__body">
                    <div><span className="source-kind">{source.kind}</span>{source.requires_ocr ? <span className="source-warning">OCR required</span> : null}</div>
                    <h3>{source.title}</h3>
                    <p>{source.extracted_text || "No extractable text found."}</p>
                  </div>
                  <button
                    className="source-open"
                    type="button"
                    disabled={jobs[source.id]?.status === "queued" || jobs[source.id]?.status === "running"}
                    onClick={() => void generate(source)}
                  >
                    {jobs[source.id]?.status === "queued"
                      ? "Queued"
                      : jobs[source.id]?.status === "running"
                        ? `Generating ${jobs[source.id]?.progress}%`
                        : jobs[source.id]?.status === "failed"
                          ? "Retry"
                          : "Generate"}
                    <ArrowRight size={16} />
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
