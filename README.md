# Gapo SlideGen

A self-hosted web application for creating, editing, presenting, and exporting
AI-assisted presentations. Turn prompts, manuscripts, or uploaded documents into
polished slide decks — entirely on your own infrastructure.

---

## ✨ Features

### AI-Powered Generation
- **One-click generation** — enter a prompt or upload a document and receive a
  complete presentation with a structured story plan.
- **Smart content layouts** — the AI selects a narrative-appropriate slide count
  (typically 5–15) and rotates through multiple layout archetypes.
- **AI rewrite** — refine a selected text element or rewrite every text block on
  a slide from a single instruction, preserving layout and styles.
- **AI image generation** — generate a 16:9 image from a prompt and place it
  directly on a slide, or let the pipeline auto-place images for
  `split-image` layouts when an image provider is configured.

### Rich Slide Editor
- Add, remove, reorder, and duplicate slides.
- Insert and format text, shapes, and images.
- Adjust image fit, alt text, and layer ordering.
- 100-step undo/redo with keyboard shortcuts.
- Keyboard-driven present mode.

### Document Ingestion
- Accepts **prompt**, **manuscript**, **DOCX**, **PPTX**, and **text PDF**
  inputs.
- Normalized content is stored per-user with automatic retention cleanup.

### Themes & Export
- Four native-editable visual themes: **Modern Blue**, **Editorial Cobalt**,
  **Warm Studio**, and **Midnight Signal**.
- Export to **native PPTX** with editable text, shapes, tables, charts, and
  embedded images.

### Security & Multi-User
- Internal email/password authentication with Argon2 hashing and revocable
  session cookies.
- Per-user data ownership — all resources are filtered by the authenticated
  owner.
- Debounced autosave with optimistic revision control prevents concurrent tabs
  from silently overwriting each other.

---

## 🏗️ Architecture

```text
gapo-slidegen/
├── apps/
│   ├── api/              Python · FastAPI backend, PostgreSQL jobs, AI providers
│   └── web/              TypeScript · Next.js frontend, editor, dashboard
├── packages/
│   ├── slide-schema/     Canonical presentation JSON schema & edit operations
│   ├── slide-editor/     Product-owned editor boundary
│   └── pptx-exporter/    Schema-to-native OOXML export adapter
├── docs/
│   ├── decisions/        Architecture & dependency decision records
│   └── provenance/       Source, license, and modification records
├── LICENSES/             Third-party license texts
├── compose.yaml          Local PostgreSQL via Docker
└── .env.example          Environment variable reference
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| [Node.js](https://nodejs.org/) | ≥ 18 | Frontend & monorepo scripts |
| [uv](https://docs.astral.sh/uv/) | latest | Python package management |
| [Docker Desktop](https://www.docker.com/) | latest | Local PostgreSQL |

### 1. Install dependencies

```bash
npm install
uv sync --project apps/api --python 3.12
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env to set your preferred AI provider (see Configuration below)
```

### 3. Start the database

```bash
npm run db:up        # Start PostgreSQL container
npm run db:migrate   # Apply database migrations
```

### 4. Launch the application

Open **four separate terminals** and run one command in each:

```bash
# Terminal 1 — Backend API
npm run api:dev

# Terminal 2 — Frontend
npm run dev --workspace @gapo-slidegen/web

# Terminal 3 — Generation worker (processes AI jobs)
npm run worker:dev

# Terminal 4 — Cleanup worker (removes expired sources)
npm run cleanup:dev
```

### 5. Open the application

Navigate to **http://localhost:3000**, register an account, and create your
first presentation.

---

## ⚙️ Configuration

All settings are configured through environment variables. Copy `.env.example`
to `.env` and adjust as needed.

### AI Providers

Generation uses a **provider** abstraction. Choose one:

| Provider | Variable Value | External API | Description |
|---|---|---|---|
| `stub` | `SLIDEGEN_GENERATION_PROVIDER=stub` | None | Deterministic offline placeholder. No data leaves the machine. |
| `google-ai-studio` | `SLIDEGEN_GENERATION_PROVIDER=google-ai-studio` | Google Gemini | Uses the Gemini Developer API for structured story plans. |
| `company-gateway` | `SLIDEGEN_GENERATION_PROVIDER=company-gateway` | Self-hosted | OpenAI-compatible gateway for internal or self-hosted LLMs. |

#### Stub (default — no setup required)

The stub provider validates the full pipeline without external calls. Useful for
development, testing, and environments without GPU or API access.

#### Google AI Studio

```dotenv
SLIDEGEN_GENERATION_PROVIDER=google-ai-studio
SLIDEGEN_GOOGLE_API_KEY=your-api-key
SLIDEGEN_GOOGLE_MODEL=gemini-2.5-pro
```

#### Company Gateway (OpenAI-compatible)

```dotenv
SLIDEGEN_GENERATION_PROVIDER=company-gateway
SLIDEGEN_COMPANY_GATEWAY_URL=http://127.0.0.1:5000
SLIDEGEN_COMPANY_GATEWAY_API_KEY=your-api-key
SLIDEGEN_COMPANY_GATEWAY_MODEL=your-model-id
```

> **Important:** `SLIDEGEN_COMPANY_GATEWAY_URL` should be the **base URL only**
> (e.g. `http://127.0.0.1:5000`). The chat completions path
> (`/v1/chat/completions`) is appended automatically.

#### Image Generation (optional)

Image generation is configured separately and is disabled by default:

```dotenv
SLIDEGEN_IMAGE_PROVIDER=google-ai-studio
SLIDEGEN_GOOGLE_IMAGE_MODEL=your-image-model-id
```

> **Note:** Restart both the API server and the generation worker after changing
> any provider settings.

### Environment Variable Reference

| Variable | Default | Description |
|---|---|---|
| `SLIDEGEN_API_INTERNAL_URL` | `http://127.0.0.1:8000` | Backend URL used by the Next.js proxy |
| `SLIDEGEN_DATABASE_URL` | `postgresql+psycopg://...` | PostgreSQL connection string |
| `SLIDEGEN_STORAGE_ROOT` | `.data/storage` | Local file storage path |
| `SLIDEGEN_MAX_UPLOAD_BYTES` | `26214400` (25 MB) | Maximum upload file size |
| `SLIDEGEN_GENERATION_CONCURRENCY` | `2` | Concurrent generation jobs |
| `SLIDEGEN_SESSION_TTL_HOURS` | `168` (7 days) | Authentication session lifetime |
| `SLIDEGEN_SOURCE_RETENTION_HOURS` | `24` | Hours before expired sources are cleaned |
| `SLIDEGEN_GENERATION_PROVIDER` | `stub` | AI text generation provider |
| `SLIDEGEN_IMAGE_PROVIDER` | `disabled` | AI image generation provider |

---

## 🔒 Data Privacy

Gapo SlideGen is designed with data privacy as a core principle:

- **Stub provider** — all processing stays on the local machine. No data is
  transmitted externally.
- **Google AI Studio** — only normalized source text (bounded to
  `SLIDEGEN_GOOGLE_MAX_INPUT_CHARS`), the requested language, and title are sent.
  Uploaded images, presentation geometry, styles, and the final document are
  **never** sent to Google.
- **AI rewrite** — only the selected text (or current slide text blocks), the
  instruction, and the language are transmitted. The full presentation is not
  sent.
- **Image generation** — only the prompt and aspect ratio are sent. No slide
  content, existing images, or presentation data is included.
- **PPTX export** — processed entirely on the local server. No external service
  is involved.

---

## 🧪 Testing

```bash
# Run all checks (TypeScript + Python)
npm run check

# TypeScript tests only
npm test

# Python API tests only
npm run api:test
```

---

## 📁 Available Scripts

| Command | Description |
|---|---|
| `npm run api:dev` | Start the FastAPI backend with hot reload |
| `npm run dev -w @gapo-slidegen/web` | Start the Next.js frontend dev server |
| `npm run worker:dev` | Start the background generation worker |
| `npm run cleanup:dev` | Start the source retention cleanup worker |
| `npm run db:up` | Start PostgreSQL via Docker Compose |
| `npm run db:migrate` | Apply Alembic database migrations |
| `npm run build` | Build all workspaces for production |
| `npm run check` | Run TypeScript type checks and Python tests |
| `npm test` | Run TypeScript test suites |
| `npm run api:test` | Run Python API test suite |

---

## 📄 License & Attribution

This project includes software derived from the following open-source projects.
See [NOTICE](NOTICE) and [LICENSES/](LICENSES/) for full details.

| Project | License | Usage |
|---|---|---|
| [Presenton](https://github.com/presenton/presenton) | Apache 2.0 | Editor patterns, template system |
| [Presentation AI](https://github.com/allweonedev/presentation-ai) | MIT | Workflow and architectural reference |
| [PptxGenJS](https://github.com/gitbrent/PptxGenJS) | MIT | PPTX export engine |

Exact upstream revisions and modified files are documented in
[docs/provenance/](docs/provenance/).
