# Gapo SlideGen — High-Level Architecture

Sơ đồ này mô tả các thành phần chính của POC và luồng từ prompt/tài liệu đến web editor, long-term memory và native editable PPTX.

```mermaid
flowchart TB
    User[User]

    subgraph Client[Web Client - Next.js]
        AuthUI[Auth and Workspace]
        InputUI[Prompt or PDF DOCX PPTX Upload]
        ReviewUI[Extracted Content and Outline Review]
        EditorUI[Slide Editor and Present Mode]
        ProgressUI[SSE Progress]
    end

    subgraph API[Application Backend - FastAPI]
        Auth[Auth and Identity Adapter]
        Presentation[Presentation Service]
        Jobs[Persistent Jobs and SSE]

        subgraph Ingestion[Document Ingestion]
            Upload[Validation and Storage Adapter]
            Parsers[PDF DOCX PPTX Parsers]
            OCRDecision{Text layer sufficient?}
            OCR[Conditional OCR<br/>Tesseract vie and eng]
            Normalize[Normalize Blocks and Provenance]
        end

        subgraph Intelligence[AI and Knowledge Layer]
            Chunk[Chunking and Local Embeddings]
            Retrieval[Scoped Memory Retrieval]
            Orchestrator[AI Orchestrator<br/>Retry Validation Failover]
            Quality[Structured Output Quality Gate]
        end

        SlideEngine[SlideDocument Engine<br/>Schemas Layouts Themes]
        PPTX[Native Editable PPTX Exporter<br/>python-pptx]
    end

    subgraph Data[Data and Storage]
        Neon[(Neon PostgreSQL<br/>Relational Data and JSONB)]
        Vector[(pgvector<br/>Document and Long-Term Memory)]
        Files[(File Storage Adapter<br/>Filesystem POC or S3-compatible later)]
    end

    subgraph Providers[AI Provider Chain]
        Gemini[1. Google Gemini<br/>Primary]
        OpenAI1[2. OpenAI<br/>Fallback 1]
        OpenAI2[3. OpenAI<br/>Fallback 2]
    end

    User --> AuthUI
    User --> InputUI
    User --> ReviewUI
    User --> EditorUI

    AuthUI --> Auth
    InputUI --> Presentation
    InputUI --> Upload
    ReviewUI --> Presentation
    Presentation --> ReviewUI
    EditorUI --> Presentation
    Presentation --> EditorUI
    Jobs --> ProgressUI

    Auth --> Neon
    Neon --> Auth
    Presentation --> Neon
    Neon --> Presentation
    Presentation --> Jobs

    Upload --> Files
    Upload --> Parsers
    Parsers --> OCRDecision
    OCRDecision -->|Yes| Normalize
    OCRDecision -->|No or scanned page| OCR
    OCR --> Normalize
    Normalize --> Neon
    Normalize --> Chunk

    Chunk --> Vector
    Presentation --> Retrieval
    Retrieval --> Vector
    Vector --> Retrieval
    Retrieval --> Orchestrator
    Presentation --> Orchestrator

    Orchestrator --> Gemini
    Gemini -. retryable failure .-> OpenAI1
    OpenAI1 -. retryable failure .-> OpenAI2
    Gemini --> Quality
    OpenAI1 --> Quality
    OpenAI2 --> Quality

    Quality --> SlideEngine
    SlideEngine --> Presentation
    SlideEngine --> EditorUI
    SlideEngine --> PPTX
    PPTX --> Files
    PPTX --> User
```

## Luồng xử lý chính

```mermaid
sequenceDiagram
    actor U as User
    participant W as Next.js
    participant A as FastAPI
    participant D as Document Pipeline
    participant M as Neon and pgvector
    participant AI as AI Orchestrator
    participant E as Slide and PPTX Engine

    U->>W: Prompt or upload PDF DOCX PPTX
    W->>A: Create presentation or upload document
    A->>D: Validate parse and conditional OCR
    D->>M: Save blocks chunks embeddings provenance
    A-->>W: Extracted content for review
    U->>W: Edit content and request outline
    W->>A: Generate outline
    A->>M: Retrieve scoped memory and document chunks
    A->>AI: Structured outline request
    AI-->>A: Validated outline
    A-->>W: Outline review
    U->>W: Approve outline and generate slides
    W->>A: Start persistent generation job
    A-->>W: SSE job and slide progress
    loop For each slide
        A->>M: Retrieve relevant context
        A->>AI: Generate structured slide
        AI-->>A: Validated SlideDocument
        A->>M: Persist slide
        A-->>W: SSE slide completed
    end
    U->>W: Edit reorder and autosave
    W->>A: Update SlideDocument
    A->>M: Persist changes
    U->>W: Export PPTX
    W->>A: Create export job
    A->>E: Map SlideDocument to native PPTX objects
    E-->>U: Editable PPTX file
```

## Ranh giới kiến trúc

- Next.js không chứa AI keys, OCR, database access hoặc business logic.
- FastAPI OpenAPI là nguồn sự thật cho frontend contracts.
- Mọi document, memory, presentation, job và export được scope explicit bằng `owner_id`.
- SSE chỉ truyền tiến trình; database là nguồn sự thật cho job state.
- Web renderer và PPTX exporter dùng chung `SlideDocument`.
- AI chỉ trả structured data; không sinh raw HTML, React hoặc JavaScript để execute.
- OCR chỉ chạy cho trang scan/image-only hoặc text layer không đủ.
- Embeddings mặc định chạy local; Neon pgvector lưu và truy xuất memory.
- PPTX export dùng native text/shapes/images/tables/charts, không flatten toàn slide thành ảnh.

## Preview

- GitHub render trực tiếp các block `mermaid` trong Markdown.
- VS Code built-in Markdown Preview có thể cần extension hỗ trợ Mermaid.
- Có thể copy riêng nội dung trong block vào Mermaid Live Editor để kiểm tra nhanh.
