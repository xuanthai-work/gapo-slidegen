# Gapo SlideGen — POC Specification

## 1. Tổng quan

Gapo SlideGen là một ứng dụng web độc lập dùng AI để tạo presentation từ prompt hoặc tài liệu. Đây là dự án greenfield, không phải fork hoặc bản tinh gọn của Presenton. Presenton và `presentation-ai` chỉ là nguồn tham khảo về workflow, template, editor và kiến trúc AI.

POC phải chứng minh được luồng frontend → backend → document processing → AI → memory → database → editable PowerPoint export. Hệ thống cần đủ rõ để trình bày seminar về AI core và đủ tách lớp để tích hợp auth/identity của Gapo ở giai đoạn sau.

Nguyên tắc phạm vi: những khả năng làm được bằng công nghệ open-source/local vẫn thuộc POC. Chỉ phụ thuộc hoặc hoãn một phần khi nó bắt buộc dùng dịch vụ ngoài có chi phí, license thương mại hoặc hạ tầng chưa được cấp.

## 2. Mục tiêu sản phẩm

POC phải cho phép người dùng:

1. Tạo tài khoản, đăng nhập và có workspace riêng.
2. Tạo presentation từ prompt hoặc upload PDF, DOCX, PPTX.
3. Xem, kiểm tra và chỉnh nội dung được trích xuất từ tài liệu.
4. OCR tài liệu scan hoặc trang không có text layer.
5. Tạo và chỉnh structured outline trước khi sinh slide.
6. Sinh slide theo thời gian thực bằng AI có provider failover.
7. Xem trước, chỉnh text, đổi thứ tự slide và trình chiếu trên web.
8. Lưu presentation, tài liệu và memory dài hạn trên workspace của người dùng.
9. Xuất `.pptx` với text, shape, image, table và chart được chỉnh sửa như PowerPoint native objects.
10. Tải lại presentation và tiếp tục làm việc ở phiên đăng nhập sau.

## 3. Phạm vi POC

### 3.1 Bắt buộc trong phạm vi

- Web app desktop-first, responsive ở mức cơ bản.
- Email/password self-registration, sign-in, sign-out.
- Dashboard và dữ liệu riêng theo user.
- Input bằng prompt, PDF, DOCX hoặc PPTX.
- Direct text extraction khi tài liệu có text.
- Conditional OCR cho PDF scan, trang ảnh hoặc nội dung không có text layer.
- OCR tiếng Việt và tiếng Anh bằng giải pháp local/open-source.
- Preview và chỉnh extracted content trước khi generation.
- Chunking, embedding và semantic retrieval trên Neon/pgvector.
- User memory, presentation memory và document knowledge memory.
- Outline-first workflow.
- Chỉnh sửa và reorder outline.
- Gemini primary, hai OpenAI fallback.
- Retry/failover hữu hạn và phân loại lỗi.
- SSE cho outline/slide/job progress.
- Structured slide JSON, không dùng raw AI-generated HTML/JS.
- 5 layout cốt lõi, có schema rõ ràng.
- 1–2 theme mặc định.
- Web preview, present mode, text editing và slide reorder.
- Autosave.
- Native editable PPTX export.
- Neon PostgreSQL, SQLAlchemy async và Alembic migrations.
- Ownership isolation cho mọi tài nguyên.
- Structured logging cho ingest, AI call, failover, retrieval và export.

### 3.2 Có thể giới hạn chất lượng/khối lượng nhưng không bỏ

- Tối đa mặc định 50 trang mỗi tài liệu và 10 slide mỗi deck; cấu hình được.
- OCR chỉ tối ưu cho tiếng Việt/Anh và tài liệu in rõ.
- PPTX import tập trung trích xuất nội dung; chưa tái tạo chính xác mọi animation/style của file gốc.
- PPTX export đảm bảo editability và fidelity cho layout do Gapo SlideGen hỗ trợ; không cam kết mọi tính năng nâng cao của PowerPoint.
- Chỉ hỗ trợ một số chart cơ bản: bar, line, pie/doughnut.
- Memory retrieval dùng vector similarity + metadata filters; chưa cần agentic multi-hop retrieval.
- File storage dùng storage adapter; POC local/self-host có thể dùng filesystem volume.
- Embedding ưu tiên model multilingual local; chỉ dùng embedding API trả phí nếu được duyệt sau benchmark.

### 3.3 Ngoài phạm vi hiện tại

- Electron hoặc native desktop app.
- Auth/SSO Gapo thực tế; chỉ chuẩn bị identity adapter.
- OAuth, MFA, email verification và forgot-password email flow.
- Organization/team/role phức tạp.
- Realtime collaboration.
- MCP server.
- Community/template marketplace.
- Import arbitrary custom PPTX thành template sinh slide hoàn chỉnh.
- Animation/transition phức tạp.
- Billing, subscription và quota thương mại.
- Web search/deep research/citation từ Internet.
- Paid OCR, paid vector DB, paid object storage hoặc paid image generation nếu chưa được cấp ngân sách.

## 4. Kiến trúc tổng thể

```text
Browser
  |
  | HTTPS / REST / SSE / file upload
  v
Next.js Web App
  |
  | JSON API + HttpOnly session cookie
  v
FastAPI Backend
  |-- Auth and identity adapter
  |-- Document ingest service
  |     |-- PDF text extraction
  |     |-- Conditional OCR
  |     |-- DOCX parser
  |     `-- PPTX parser
  |-- Chunking, embedding and retrieval
  |-- Presentation and memory services
  |-- AI orchestration and failover
  |-- Slide schema/quality validation
  |-- Persistent jobs + SSE
  `-- Native PPTX export service
         |
         |-- Neon PostgreSQL + pgvector
         |-- File storage adapter
         |-- Google Gemini primary
         `-- OpenAI fallbacks
```

Frontend không được gọi trực tiếp AI provider, database hoặc OCR service. API key, embedding model, retrieval, failover và export chỉ chạy ở backend.

POC có thể chạy worker trong cùng deployment nhưng job state phải persist trong database. Service interface phải cho phép tách worker/queue ở giai đoạn production.

## 5. Technology stack

### 5.1 Frontend

- Next.js App Router.
- React + TypeScript.
- Tailwind CSS.
- shadcn/ui hoặc Radix UI.
- TanStack Query cho server state/mutation.
- Zustand cho editor draft, selection và undo/redo.
- dnd-kit cho outline/slide reorder.
- Zod cho client validation khi phù hợp.

### 5.2 Backend

- Python 3.11.
- FastAPI + Pydantic v2.
- SQLAlchemy 2 async + `asyncpg`.
- Alembic migrations.
- SDK chính thức của Gemini/OpenAI hoặc `httpx` adapter.
- SSE cho generation events.
- Argon2 hoặc bcrypt cho password hashing.
- `python-pptx` cho PPTX read/export.
- `python-docx` cho DOCX extraction.
- PyMuPDF hoặc `pdfplumber` cho PDF extraction/rendering.
- Tesseract + `pytesseract` cho OCR local.
- `pgvector`/SQLAlchemy vector type cho semantic memory.
- Local multilingual embedding model qua sentence-transformers, FastEmbed hoặc ONNX runtime.

### 5.3 Database và storage

- Neon PostgreSQL.
- Pooled URL cho app runtime.
- Direct URL cho Alembic khi cần.
- `CREATE EXTENSION vector` qua migration/setup được kiểm soát.
- JSONB cho outline, slide content và metadata.
- Vector column cho document/user memory embeddings.
- Storage adapter với filesystem volume cho POC; có thể thay S3-compatible storage sau.

Neon vận hành PostgreSQL; Alembic vẫn là nguồn quản lý phiên bản schema.

## 6. Cấu trúc repository dự kiến

```text
gapo-slidegen/
|-- apps/
|   |-- web/                       # Next.js
|   `-- api/                       # FastAPI
|       |-- app/
|       |   |-- api/
|       |   |-- auth/
|       |   |-- ai/
|       |   |-- documents/
|       |   |-- memory/
|       |   |-- presentations/
|       |   |-- exports/
|       |   |-- jobs/
|       |   |-- db/
|       |   `-- core/
|       |-- alembic/
|       |-- tests/
|       `-- pyproject.toml
|-- packages/
|   `-- contracts/                 # OpenAPI-generated frontend types
|-- storage/                        # Ignored local POC volume
|-- .env.example
|-- docker-compose.yml
|-- README.md
|-- PRESENTON_TECH_REUSE.md
`-- SPEC.md
```

Không đặt AI/business logic trong Next.js route handlers.

## 7. Luồng người dùng

### 7.1 Authentication

```text
Sign up -> validate -> create user -> session -> dashboard
Sign in -> verify password -> HttpOnly session -> dashboard
```

### 7.2 Prompt-only generation

```text
Prompt/options
  -> create draft presentation
  -> retrieve relevant user/presentation memory
  -> generate structured outline
  -> user edits outline
  -> generate slides via SSE
  -> validate and persist
  -> editor/present/export
```

### 7.3 Document-grounded generation

```text
Upload PDF/DOCX/PPTX
  -> validate and store
  -> extract structured blocks
  -> detect pages requiring OCR
  -> OCR only where needed
  -> preview/edit extracted content
  -> chunk + embed + persist source references
  -> retrieve relevant chunks
  -> generate outline grounded in documents
  -> generate/edit/export slides
```

## 8. Document ingestion và OCR

### 8.1 Common document model

Mọi parser phải trả về cùng schema:

```json
{
  "type": "heading",
  "text": "Kết quả kinh doanh Q2",
  "page_number": 3,
  "slide_number": null,
  "level": 1,
  "source_document_id": "uuid",
  "metadata": {}
}
```

Block types tối thiểu: `title`, `heading`, `paragraph`, `list_item`, `table`, `image_text`.

### 8.2 PDF strategy

1. Thử extract text theo trang.
2. Đánh giá text length/density và image-only signals.
3. Trang có text layer tốt: dùng direct extraction.
4. Trang scan/ít text: render ảnh và OCR.
5. Lưu provenance theo page và extraction method.

Không OCR toàn bộ PDF mặc định vì chậm và có thể làm giảm chất lượng text vốn đã extract được.

### 8.3 DOCX strategy

- Trích heading, paragraph, list và table theo thứ tự.
- Giữ heading level và section structure.
- Trích alt text/image metadata nếu khả thi.

### 8.4 PPTX strategy

- Trích title, text run, bullet, table và speaker notes khi hỗ trợ.
- Giữ slide number và shape order cơ bản.
- Có thể OCR image-only slides ở chế độ hi-res/explicit fallback.
- Không cam kết giữ animation, transition hoặc mọi style gốc.

### 8.5 Extracted content review

User phải xem được:

- Nội dung theo file/page/slide.
- Trang đã OCR.
- Cảnh báo text ít hoặc OCR confidence thấp nếu có.
- Khả năng sửa text trước khi đưa vào AI context.

## 9. AI core

### 9.1 AI capabilities

- Hiểu prompt/options và document context.
- Sinh structured outline.
- Sinh content cho từng predefined layout.
- Chọn layout phù hợp trong allowlist.
- Tạo speaker notes.
- Regenerate outline, toàn deck hoặc một slide với instruction.
- Retrieval từ document/user/presentation memory.
- Không tự bịa số liệu khi nguồn không cung cấp; đánh dấu nội dung cần xác minh.
- Giữ source references ở mức page/slide cho nội dung grounded.

### 9.2 Provider chain

1. Google Gemini — primary.
2. OpenAI fallback 1.
3. OpenAI fallback 2.

```env
AI_PRIMARY_PROVIDER=google
GOOGLE_MODEL=gemini-2.5-flash
OPENAI_FALLBACK_MODEL=gpt-4.1
OPENAI_FALLBACK_2_MODEL=gpt-4.1-mini
```

Model IDs phải cấu hình, không hard-code, và được xác minh theo account tại thời điểm triển khai.

### 9.3 Failover policy

Failover khi timeout, `429`, retryable network error, provider `5xx`, hoặc output không validate sau retry budget.

Không failover vô điều kiện đối với invalid request, policy refusal, invalid credentials hoặc programming error. Mỗi provider có timeout, retry count và backoff hữu hạn.

### 9.4 Provider abstraction

```python
class AIProvider(Protocol):
    async def generate_structured(
        self,
        messages: list[Message],
        response_model: type[T],
    ) -> T: ...
```

Business service không phụ thuộc trực tiếp Gemini/OpenAI SDK.

### 9.5 Structured output và quality gate

AI không sinh raw HTML/React/JavaScript. Output phải qua Pydantic validation và quality rules:

- Layout nằm trong allowlist.
- Đủ required fields.
- Title/bullet không vượt giới hạn.
- Không quá nhiều bullet.
- Không trùng đáng kể với slide trước.
- Đúng ngôn ngữ/tone.
- Layout tương thích content.
- Số liệu không có nguồn phải được đánh dấu hoặc loại bỏ.

Nếu fail, retry repair một lần rồi mới chuyển provider theo policy.

## 10. Slide document và renderer

Web renderer và PPTX exporter phải dùng cùng một `SlideDocument` làm nguồn sự thật.

```json
{
  "layout": "two_columns",
  "elements": [
    {
      "type": "text",
      "x": 0.7,
      "y": 0.4,
      "w": 11.9,
      "h": 0.7,
      "text": "Cơ hội và thách thức",
      "style": {
        "fontSize": 28,
        "bold": true,
        "color": "#172B4D"
      }
    }
  ],
  "speakerNotes": ""
}
```

Coordinate system phải map xác định giữa canvas 16:9 và PowerPoint inches/EMU. Element types bắt buộc: text, shape, image, table và chart cơ bản.

Layout cốt lõi:

- `title`.
- `title_bullets`.
- `two_columns`.
- `statistic`.
- `quote`.

## 11. Native editable PPTX export

Không được export bằng cách chụp toàn slide thành ảnh.

Mapping bắt buộc:

| Slide element | PPTX output |
|---|---|
| Title/body | Native text box/runs |
| Bullet list | Native paragraphs |
| Background | Native fill |
| Rectangle/circle/line | Native shape |
| Table | Native PowerPoint table |
| Supported chart | Native editable chart |
| Image | Native picture |
| Speaker notes | Notes nếu thư viện hỗ trợ ổn định |

Export dùng `python-pptx` trước. Nếu benchmark cho thấy giới hạn fidelity không chấp nhận được, đánh giá PptxGenJS sau nhưng không làm mất single-source-of-truth schema.

PPTX phải mở được trong Microsoft PowerPoint và được smoke-test với LibreOffice. Text và shape phải chọn, sửa, di chuyển và resize độc lập.

## 12. Long-term memory và retrieval

### 12.1 Memory scopes

**User memory**

- Ngôn ngữ/tone/số slide mặc định.
- Brand colors và font preferences.
- Audience hoặc writing preferences được user xác nhận.

**Presentation memory**

- Outline đã duyệt.
- Terminology.
- Slide/edit history cần thiết.
- Feedback như “ngắn hơn” hoặc “tập trung vào ROI”.

**Knowledge memory**

- Document blocks/chunks.
- Embeddings.
- Page/slide references.
- Ownership, provenance và retention metadata.

### 12.2 Memory rules

- Không tự coi mọi AI output là user preference.
- Chỉ ghi preference khi user cấu hình, xác nhận hoặc pattern được thiết kế rõ.
- Memory phải có scope, source, timestamp và confidence khi phù hợp.
- User phải xem, sửa và xóa memory của mình.
- Retrieval luôn filter theo `owner_id` và scope trước semantic similarity.
- Local multilingual embedding là mặc định để tránh external embedding cost.

### 12.3 Retrieval flow

```text
Current prompt/task
  -> embedding
  -> metadata/ownership filter
  -> pgvector similarity search
  -> top-k chunks/memories
  -> context budget/rerank đơn giản
  -> AI prompt with provenance
```

## 13. Authentication và tích hợp sau này

POC sử dụng email/password, password hash và HttpOnly cookie. Production bật `Secure`, cấu hình `SameSite`, CORS và CSRF phù hợp. Register/login có rate limit.

Business service chỉ nhận identity chuẩn hóa:

```python
class CurrentUser(BaseModel):
    id: UUID
    email: str
    roles: list[str] = []
```

```text
POC session/JWT -> CurrentUser
Gapo identity/JWT -> CurrentUser
```

Presentation/document/memory services không tự đọc hoặc verify raw token.

## 14. Database schema ban đầu

### 14.1 Core tables

**`users`**: `id`, `email`, `password_hash`, `display_name`, `is_active`, timestamps.

**`presentations`**: `id`, `owner_id`, `title`, `prompt`, `language`, `slide_count`, `status`, `theme_key`, `outline JSONB`, timestamps.

**`slides`**: `id`, `presentation_id`, `position`, `layout_key`, `document JSONB`, `speaker_notes`, timestamps.

**`generation_jobs`**: `id`, `presentation_id`, `owner_id`, `type`, `status`, `current_step`, `progress`, `provider`, `model`, sanitized error, timestamps.

### 14.2 Document and memory tables

**`documents`**

- `id`, `owner_id`, original filename, MIME type, size.
- Storage key, status, page/slide count.
- Parser/OCR metadata and timestamps.

**`document_blocks`**

- `id`, `document_id`, owner, type, text.
- Page/slide number, order, extraction method, metadata JSONB.

**`document_chunks`**

- `id`, `document_id`, owner, content.
- Source page/slide range, metadata JSONB.
- `embedding VECTOR(n)`.

**`user_memories`**

- `id`, `owner_id`, kind, content, metadata.
- Optional embedding, confidence, source and timestamps.

**`presentation_memories`**

- `id`, `presentation_id`, `owner_id`, kind, content.
- Optional embedding, source and timestamps.

**`presentation_documents`**

- Join table giữa presentation và source documents.

**`exports`**

- `id`, `presentation_id`, `owner_id`, format, status, storage key, error, timestamps.

### 14.3 Ownership

Mọi query resource phải scope explicit theo current user:

```sql
SELECT * FROM presentations
WHERE id = :presentation_id
  AND owner_id = :current_user_id;
```

## 15. API contract dự kiến

### 15.1 Auth

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
```

### 15.2 Documents

```text
POST   /api/v1/documents
GET    /api/v1/documents
GET    /api/v1/documents/{document_id}
GET    /api/v1/documents/{document_id}/content
PATCH  /api/v1/documents/{document_id}/content
DELETE /api/v1/documents/{document_id}
POST   /api/v1/documents/{document_id}/reprocess
```

### 15.3 Presentations, outline và slides

```text
GET    /api/v1/presentations
POST   /api/v1/presentations
GET    /api/v1/presentations/{presentation_id}
PATCH  /api/v1/presentations/{presentation_id}
DELETE /api/v1/presentations/{presentation_id}
POST   /api/v1/presentations/{presentation_id}/outline/generate
PUT    /api/v1/presentations/{presentation_id}/outline
POST   /api/v1/presentations/{presentation_id}/generate
PATCH  /api/v1/slides/{slide_id}
POST   /api/v1/slides/{slide_id}/regenerate
POST   /api/v1/presentations/{presentation_id}/slides/reorder
DELETE /api/v1/slides/{slide_id}
```

### 15.4 Jobs/SSE

```text
GET /api/v1/jobs/{job_id}
GET /api/v1/jobs/{job_id}/events
```

Events tối thiểu:

```text
job.started
document.extracting
document.ocr_started
document.completed
outline.started
outline.completed
slide.started
slide.completed
slide.failed
export.started
export.completed
job.completed
job.failed
```

### 15.5 Memory

```text
GET    /api/v1/memories
POST   /api/v1/memories
PATCH  /api/v1/memories/{memory_id}
DELETE /api/v1/memories/{memory_id}
```

### 15.6 Export

```text
POST /api/v1/presentations/{presentation_id}/exports/pptx
GET  /api/v1/exports/{export_id}
GET  /api/v1/exports/{export_id}/download
```

FastAPI OpenAPI là nguồn sự thật; frontend types được generate từ OpenAPI.

## 16. Frontend routes dự kiến

```text
/sign-up
/sign-in
/dashboard
/documents
/documents/{id}/review
/presentations/new
/presentations/{id}/outline
/presentations/{id}/edit
/presentations/{id}/present
/settings/memory
```

## 17. Environment variables

```env
# App
APP_ENV=development
WEB_ORIGIN=http://localhost:3000
API_ORIGIN=http://localhost:8000
SESSION_SECRET=
FILE_STORAGE_BACKEND=filesystem
FILE_STORAGE_PATH=./storage

# Neon
DATABASE_URL=postgresql+asyncpg://user:password@pooled-host/database?ssl=require
DATABASE_URL_DIRECT=postgresql+asyncpg://user:password@direct-host/database?ssl=require

# AI failover
AI_PRIMARY_PROVIDER=google
GOOGLE_API_KEY=
GOOGLE_MODEL=gemini-2.5-flash
OPENAI_API_KEY=
OPENAI_FALLBACK_MODEL=gpt-4.1
OPENAI_FALLBACK_2_MODEL=gpt-4.1-mini

# Local embedding/OCR
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=
OCR_LANGUAGES=vie+eng
TESSERACT_CMD=

# Limits
AI_REQUEST_TIMEOUT_SECONDS=60
AI_MAX_RETRIES_PER_PROVIDER=1
MAX_SLIDES_PER_PRESENTATION=10
MAX_DOCUMENT_PAGES=50
MAX_UPLOAD_SIZE_MB=50
```

Không đặt secret trong `NEXT_PUBLIC_*`, Git hoặc response frontend.

## 18. Non-functional requirements

### 18.1 Security

- Validate MIME bằng content, không chỉ extension.
- Giới hạn file size/page count và chống zip bomb cho DOCX/PPTX.
- Randomized storage key; không dùng filename làm filesystem path.
- Không execute macro/script từ tài liệu.
- Sanitize extracted/AI text khi render.
- Ownership test cho document, memory, presentation, slide, job và export.
- Không log secret, password, raw token hoặc full sensitive document content.
- CORS/CSRF/session cookie cấu hình theo môi trường.
- Error client không chứa stack trace hoặc provider secret.

### 18.2 Reliability

- Parser/OCR/AI/export đều có timeout và trạng thái job persisted.
- Retry hữu hạn, idempotency phù hợp và sanitized errors.
- Client reconnect đọc lại trạng thái job từ database.
- Autosave debounce và tránh silent overwrite.
- Upload/extraction failure không làm mất file hoặc presentation metadata ngoài ý muốn.

### 18.3 Observability

Log metadata: request/job/presentation/document ID, stage, provider/model, latency, attempt, token usage, parser/OCR method, retrieved chunk count và export duration. Không log raw content mặc định ở production.

### 18.4 Performance mục tiêu POC

- API không gọi tác vụ nặng phản hồi dưới 500 ms bình thường.
- Upload tạo job và trả trạng thái nhanh.
- Trang có text không bị OCR lại.
- User thấy generation progress liên tục.
- Retrieval top-k có index/filter phù hợp.

## 19. Testing strategy

### 19.1 Backend

- Auth và two-user ownership tests.
- Alembic migration test trên PostgreSQL.
- PDF text và scanned-PDF fixtures.
- DOCX/PPTX extraction fixtures.
- OCR conditional routing test.
- Chunking, pgvector ownership filter và memory CRUD tests.
- AI structured schema, quality gate và failover mocks.
- SSE event order/reconnect tests.
- Native PPTX export test: unzip/XML smoke checks và reopen bằng `python-pptx`.
- Assert text/shapes/tables/charts không bị flatten thành full-slide image.

### 19.2 Frontend/E2E

- Auth guard.
- Upload/progress/extracted content review.
- Outline edit/reorder.
- Slide renderer và editor autosave.
- Generation/error/failover UI.
- E2E: sign up → upload document → review → outline → slides → edit → export PPTX → reopen presentation.

## 20. Kế hoạch một tháng

### Tuần 1 — Foundation, auth và ingest

- Scaffold/ổn định Next.js + FastAPI.
- Neon, pgvector, SQLAlchemy và Alembic.
- Auth + ownership.
- Storage adapter và upload validation.
- PDF/DOCX/PPTX extraction.
- Conditional OCR và extracted-content review.

Deliverable: user upload và review được ba format, bao gồm PDF scan.

### Tuần 2 — Memory và AI outline

- Chunking + local multilingual embeddings.
- User/presentation/document memory.
- Gemini + OpenAI provider chain.
- Document-grounded outline generation.
- Quality validation và source provenance.

Deliverable: prompt/tài liệu tạo được outline, memory tồn tại qua phiên.

### Tuần 3 — Slide generation và editor

- `SlideDocument` schemas và five-layout renderer.
- Persistent generation jobs + SSE.
- Slide generation/regeneration.
- Editor, reorder, autosave và present mode.

Deliverable: deck hoàn chỉnh dùng được trên web.

### Tuần 4 — Editable PPTX và stabilization

- Native `python-pptx` exporter.
- Text/shape/table/chart/image mappings.
- Fidelity/overflow/font tests.
- Security, ownership và failover tests.
- Metrics, architecture docs, seminar và demo fallback.

Deliverable: editable PPTX và POC end-to-end ổn định.

Nếu timeline bị ép, giảm số layout/chart và giới hạn tài liệu; không loại bỏ ingest, conditional OCR, memory hoặc editable PPTX.

## 21. Acceptance criteria

POC hoàn thành khi:

1. User tự đăng ký, đăng nhập, đăng xuất.
2. Hai user không truy cập được document, memory, presentation, job hoặc export của nhau.
3. Upload và extract được PDF có text, DOCX và PPTX.
4. PDF scan/image-only được OCR tiếng Việt/Anh; PDF có text không bị OCR toàn bộ.
5. User xem và sửa extracted content trước generation.
6. Document chunks và embeddings được lưu/retrieve bằng Neon pgvector với source page/slide.
7. User/presentation memory tồn tại qua logout/login và có thể xem/sửa/xóa.
8. Prompt hoặc tài liệu tạo được structured outline và outline chỉnh sửa được.
9. Hệ thống tạo 5–8 slide, stream progress bằng SSE và validate mọi slide.
10. Gemini retryable failure chuyển sang OpenAI fallback và ghi model/provider đã dùng.
11. User sửa text, reorder, autosave và present deck trên web.
12. Export được `.pptx` mở thành công; text, shapes, images, tables và supported charts chỉnh sửa độc lập, không flatten cả slide thành ảnh.
13. Presentation mở lại được sau reload/sign-in lại.
14. Không lộ API key, password hoặc sensitive token vào frontend/log/Git.
15. Có automated tests cho auth, ownership, ingest/OCR, memory, failover, SSE và PPTX export.
16. Có architecture/AI-core documentation và seminar demo.

## 22. Chi phí và dependency policy

Mặc định ưu tiên:

- Tesseract OCR local.
- Local multilingual embeddings.
- Neon/pgvector thay vector DB riêng.
- Filesystem volume qua storage adapter cho POC/self-host.
- `python-pptx`, `python-docx`, PyMuPDF/pdfplumber.

Không tự ý thêm paid OCR, paid vector DB, paid storage, paid reranking, commercial font hoặc paid image provider. AI API và Neon plan là các dependency được cấu hình bởi người triển khai; nếu free tier không đủ phải báo rõ trước khi mở rộng chi phí.

## 23. Seminar deliverables

- Outline-first và document-grounded workflow.
- Direct extraction so với conditional OCR.
- Chunking, embeddings, pgvector và memory scopes.
- Structured JSON so với raw HTML.
- Provider abstraction/failover/error taxonomy.
- SSE/persistent job flow.
- Single-source-of-truth slide schema.
- Native editable PPTX mapping và fidelity trade-offs.
- Ownership/identity abstraction cho tích hợp Gapo.
- Latency, token usage, OCR quality và failover metrics.
- Giới hạn POC và roadmap.

## 24. Quyết định đã chốt

- Xây application mới hoàn toàn; Presenton chỉ là reference.
- Web-only, không Electron.
- Next.js frontend; Python/FastAPI backend.
- Neon PostgreSQL + pgvector, SQLAlchemy async và Alembic.
- POC có self-registration/sign-in và identity adapter.
- Input bắt buộc: prompt, PDF, DOCX, PPTX.
- OCR conditional, local, tiếng Việt/Anh.
- Long-term memory bắt buộc và user-manageable.
- Gemini primary; hai OpenAI fallbacks.
- Structured slide JSON và predefined layouts.
- SSE + persistent job status.
- Native editable PPTX bắt buộc; không screenshot toàn slide.
- Chỉ dừng dependency ngoài khi bắt buộc phát sinh chi phí chưa được duyệt.

## 25. Cần xác nhận trước tích hợp Gapo

- JWT/session/OAuth/OIDC và issuer/JWKS.
- Claims `user_id`, `org_id`, roles/permissions.
- Domain, API gateway và service-to-service auth.
- Ownership là user hay organization.
- Object storage nội bộ/S3-compatible.
- Event bus/webhook sau generation.
- Retention, deletion, audit và AI data policies.
- Quyền dùng model/API, quota và chi phí được cấp.

## 26. Nguyên tắc triển khai

- Làm vertical slices, không xây hết UI trước backend.
- Slice 1: sign up → upload → extract/OCR → review.
- Slice 2: chunk/memory → document-grounded outline.
- Slice 3: outline → streamed slides → editor.
- Slice 4: same slide schema → editable PPTX.
- Mỗi resource có ownership tests từ lúc tạo endpoint.
- Giảm breadth trước khi bỏ core capability.
- Mọi thay đổi scope cập nhật `SPEC.md` trong cùng PR.
