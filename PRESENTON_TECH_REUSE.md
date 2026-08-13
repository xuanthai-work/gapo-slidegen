# Presenton Technology Reuse Assessment

## 1. Mục đích

Tài liệu này xác định những công nghệ, pattern kiến trúc và ý tưởng có thể tham khảo hoặc tái sử dụng từ Presenton khi xây dựng Gapo SlideGen.

Gapo SlideGen là một ứng dụng greenfield. Presenton không phải runtime dependency và không được copy toàn bộ source sang dự án mới. Mục tiêu là chọn những pattern đã chứng minh hữu ích, sau đó triển khai lại theo phạm vi POC nhỏ và dễ kiểm soát hơn.

## 2. Tổng kết quyết định

| Thành phần | Presenton | Quyết định cho Gapo SlideGen |
|---|---|---|
| Frontend | Next.js, React, TypeScript | Sử dụng cùng stack |
| UI | Tailwind CSS, Radix UI | Sử dụng Tailwind + shadcn/ui hoặc Radix |
| Backend | FastAPI, Pydantic | Sử dụng cùng stack |
| Database access | SQLModel/SQLAlchemy async | Dùng SQLAlchemy 2 async |
| Migration | Alembic | Sử dụng Alembic với Neon |
| Streaming | SSE | Sử dụng cho generation progress |
| AI output | Structured JSON | Sử dụng bắt buộc |
| Template | JSON schema và predefined layouts | Viết phiên bản đơn giản hơn |
| Editor | Component-based slide editor | Tham khảo interaction, tự triển khai |
| Multi-user | `owner_id` scoping | Áp dụng ngay từ đầu |
| AI provider | Provider configuration/abstraction | Thiết kế lại và bổ sung failover |
| Export | Chromium và export runtime riêng | Không đưa vào core POC ban đầu |
| Desktop | Electron | Không sử dụng |

## 3. Những phần nên áp dụng

### 3.1 Outline-first workflow

Workflow cốt lõi:

```text
Prompt
  -> AI sinh structured outline
  -> người dùng xem và chỉnh outline
  -> AI sinh nội dung từng slide
  -> validate bằng schema
  -> renderer áp predefined layout
```

Lợi ích:

- Người dùng kiểm soát cấu trúc trước khi tốn chi phí tạo cả deck.
- Giảm khả năng deck sai trọng tâm.
- Chia AI pipeline thành các bước dễ test và retry.
- Có thể thay model cho từng bước sau này.

Source Presenton dùng để tham khảo:

```text
servers/fastapi/utils/llm_calls/generate_presentation_outlines.py
servers/fastapi/utils/llm_calls/generate_presentation_structure.py
servers/fastapi/utils/llm_calls/generate_slide_content.py
```

Nên tham khảo cách phân chia pipeline, prompt context và structured response. Không copy nguyên prompt vì Gapo SlideGen có schema và scope nhỏ hơn.

### 3.2 Structured slide schema

AI không được sinh React component, JavaScript hoặc HTML tùy ý trong core POC. AI chỉ sinh dữ liệu theo schema đã định nghĩa; frontend chịu trách nhiệm render.

Ví dụ TypeScript:

```ts
type Slide =
  | TitleSlide
  | TitleBulletsSlide
  | TwoColumnSlide
  | StatisticSlide
  | QuoteSlide;
```

Ví dụ payload:

```json
{
  "layout": "two_columns",
  "title": "Cơ hội và thách thức",
  "left": {
    "heading": "Cơ hội",
    "items": ["Tăng năng suất", "Giảm chi phí"]
  },
  "right": {
    "heading": "Thách thức",
    "items": ["Dữ liệu", "Nhân lực"]
  },
  "speaker_notes": ""
}
```

Source Presenton dùng để tham khảo:

```text
servers/fastapi/templates/v2/schema.py
servers/fastapi/templates/v2/models/
servers/nextjs/lib/template-v2-json-to-html.ts
```

Không nên copy toàn bộ Template V2 schema vì nó hỗ trợ nhiều element và compatibility case ngoài phạm vi POC.

### 3.3 Template và slide design

Presenton có các bộ template:

```text
dynamic
editorial
executive
general
modern
momentum
standard
swift
```

Có thể tham khảo:

- Typography hierarchy.
- Color palette.
- Khoảng cách và alignment.
- Tỷ lệ text/hình ảnh.
- Cách bố trí title, bullet, statistic, quote và column.
- Theme metadata và thumbnail.

Gapo SlideGen chỉ nên bắt đầu với:

- 1–2 theme.
- 5 layout: title, title-bullets, two-columns, statistic và quote.
- Slide aspect ratio 16:9.
- Component renderer type-safe.

Source tham khảo:

```text
templates/*/template.json
templates/*/static/
```

Nếu copy trực tiếp template, font, SVG hoặc image asset thì phải kiểm tra license và giữ attribution/NOTICE cần thiết.

### 3.4 Slide renderer

Presenton có hệ thống chuyển template JSON thành HTML và editor component. Gapo SlideGen nên triển khai renderer đơn giản bằng React components:

```tsx
export function SlideRenderer({ slide }: { slide: Slide }) {
  switch (slide.layout) {
    case "title":
      return <TitleSlide slide={slide} />;
    case "title_bullets":
      return <TitleBulletsSlide slide={slide} />;
    case "two_columns":
      return <TwoColumnSlide slide={slide} />;
    case "statistic":
      return <StatisticSlide slide={slide} />;
    case "quote":
      return <QuoteSlide slide={slide} />;
  }
}
```

Ưu điểm:

- Type-safe.
- Dễ test.
- Dễ chỉnh sửa.
- Không execute code do AI sinh.
- Dễ kiểm soát responsive behavior và overflow.

Source Presenton dùng để tham khảo:

```text
servers/nextjs/components/slide-editor/
servers/nextjs/lib/template-v2-json-to-html.ts
```

### 3.5 SSE streaming

Presenton sử dụng streaming để người dùng thấy tiến trình thay vì chờ toàn bộ deck.

Gapo SlideGen sử dụng Server-Sent Events cho các event:

```text
job.started
outline.started
outline.completed
slide.started
slide.completed
slide.failed
job.completed
job.failed
```

Source Presenton dùng để tham khảo:

```text
servers/fastapi/utils/sse.py
servers/fastapi/api/v1/ppt/endpoints/outlines.py
servers/fastapi/api/v1/ppt/endpoints/presentation.py
```

Generation job và progress phải được persist trong Neon. SSE connection không phải nguồn sự thật duy nhất.

### 3.6 AI provider abstraction

Presenton đã tách phần cấu hình provider và model khỏi nhiều phần nghiệp vụ.

Source tham khảo:

```text
servers/fastapi/utils/llm_config.py
servers/fastapi/utils/llm_provider.py
servers/fastapi/enums/llm_provider.py
```

Gapo SlideGen cần thiết kế interface mới:

```python
class AIProvider(Protocol):
    async def generate_structured(
        self,
        messages: list[Message],
        response_model: type[T],
    ) -> T:
        ...
```

Provider chain:

```text
Gemini primary
  -> OpenAI fallback model 1
  -> OpenAI fallback model 2
```

Presenton hiện không cung cấp failover đúng theo yêu cầu này. Failover orchestration phải được viết mới và có timeout, retry budget cùng error classification rõ ràng.

### 3.7 Database ownership isolation

Presenton gắn `owner_id` vào presentation, slide, asset và task để cô lập dữ liệu người dùng.

Source tham khảo:

```text
servers/fastapi/services/database.py
servers/fastapi/models/sql/presentation.py
servers/fastapi/models/sql/slide.py
```

Gapo SlideGen nên dùng explicit ownership query thay vì global ORM event magic:

```python
statement = select(Presentation).where(
    Presentation.id == presentation_id,
    Presentation.owner_id == current_user.id,
)
```

Lợi ích:

- Dễ review security.
- Dễ test từng repository/service.
- Tránh vô tình bypass global filter trong query đặc biệt.

### 3.8 Auth architecture

Source Presenton dùng để tham khảo:

```text
servers/fastapi/api/v1/auth/
servers/fastapi/api/middlewares.py
```

Nên lấy các nguyên tắc:

- Password hashing.
- HttpOnly cookie.
- `CurrentUser` dependency.
- Ownership isolation.
- Không trả password hash hoặc secret về frontend.

Không lấy:

- First-admin bootstrap.
- API-key administration.
- Codex OAuth.
- Legacy credential migration.
- Electron auth bypass.

POC chỉ cần:

```text
POST /auth/register
POST /auth/login
POST /auth/logout
GET  /auth/me
```

Auth phải nằm sau một identity adapter để có thể thay bằng JWT/identity của Gapo khi tích hợp.

### 3.9 Editor state và interaction

Presenton dùng Redux Toolkit, undo/redo và autosave.

Source tham khảo:

```text
servers/nextjs/store/slices/presentationGeneration.ts
servers/nextjs/store/slices/undoRedoSlice.ts
servers/nextjs/components/slide-editor/
```

Có thể tham khảo:

- Local update trước khi autosave.
- Debounced autosave.
- Undo/redo state.
- Reorder slide.
- Loading và streaming state.

Gapo SlideGen dự kiến dùng:

- TanStack Query cho server state.
- Zustand cho editor draft và undo/redo.
- dnd-kit cho reorder.

## 4. Những phần có thể bổ sung sau POC core

### 4.1 Image generation

Presenton hỗ trợ nhiều image provider và stock image service.

Source tham khảo:

```text
servers/fastapi/services/image_generation_service.py
servers/fastapi/utils/image_provider.py
servers/fastapi/api/v1/ppt/endpoints/images.py
```

Không đưa vào milestone đầu. Ban đầu sử dụng:

- Gradient/background.
- CSS shapes.
- Lucide icons.
- Placeholder image.

Chỉ thêm image generation sau khi pipeline text-to-slide ổn định.

### 4.2 PDF/PPTX export

Presenton dùng Chromium và presentation-export runtime riêng. Hệ thống này tương đối nặng và làm tăng đáng kể thời gian build/deploy.

Trong POC:

- Present mode là bắt buộc.
- PDF export là optional milestone.
- Editable PPTX nằm ngoài scope.

Không copy Docker/export stack của Presenton vào giai đoạn đầu.

### 4.3 Document upload

Presenton dùng LiteParse, OCR và document conversion service. Đây là dependency lớn và không cần cho prompt-first POC.

Chỉ nghiên cứu lại nếu roadmap sau POC yêu cầu:

- PDF to presentation.
- DOCX/PPTX import.
- OCR.

## 5. Những phần không sử dụng

Không đưa các thành phần sau từ Presenton sang Gapo SlideGen POC:

- Electron.
- Dockerfile đầy đủ của Presenton.
- Chromium/export runtime trong core milestone.
- LiteParse và OCR.
- MCP server.
- Mem0.
- FastEmbed cache và icon vector store.
- Community presentation API.
- Webhook system.
- Custom PPTX template import.
- Codex OAuth/Sign in with ChatGPT.
- Legacy database migrations.
- Multi-provider settings UI phức tạp.
- Raw HTML smart-generation mode.
- File `presentation.py` nguyên khối.

## 6. Stack cuối cùng của Gapo SlideGen POC

```text
Frontend
|-- Next.js
|-- React + TypeScript
|-- Tailwind CSS
|-- shadcn/ui hoặc Radix UI
|-- TanStack Query
|-- Zustand
`-- dnd-kit

Backend
|-- Python 3.11
|-- FastAPI
|-- Pydantic v2
|-- SQLAlchemy 2 async
|-- Alembic
|-- asyncpg
`-- SSE

Infrastructure
|-- Neon PostgreSQL
|-- Google Gemini primary
`-- OpenAI fallback x2
```

## 7. Thứ tự áp dụng

1. Tạo Next.js và FastAPI applications.
2. Kết nối Neon bằng SQLAlchemy async và Alembic.
3. Xây auth cơ bản cùng ownership isolation.
4. Định nghĩa outline và năm slide schemas.
5. Xây AI provider interface.
6. Xây Gemini primary và hai OpenAI fallback.
7. Hoàn thành vertical slice `prompt -> outline`.
8. Thêm generation job và SSE.
9. Xây React slide renderer.
10. Thêm edit, reorder, autosave và present mode.

## 8. Quy tắc license và attribution

Presenton sử dụng Apache License 2.0. Khi chỉ tham khảo ý tưởng hoặc pattern và tự triển khai code mới, không tạo runtime dependency vào Presenton.

Nếu copy hoặc sửa trực tiếp source, template, image, SVG, font hoặc asset từ Presenton:

- Kiểm tra license của từng asset.
- Giữ copyright notice liên quan.
- Giữ LICENSE/NOTICE theo yêu cầu Apache 2.0.
- Ghi rõ phần đã thay đổi khi cần.
- Không giả định mọi font/image trong repository có cùng quyền tái phân phối.

Ưu tiên triển khai lại schema, renderer và design system của Gapo SlideGen thay vì copy nguyên template engine.

## 9. Kết luận

Những phần đáng học sâu nhất từ Presenton là:

1. Outline-first workflow.
2. Structured slide schema.
3. Predefined template/layout renderer.
4. SSE generation flow.
5. Ownership isolation.
6. Provider abstraction.

Những phần phải viết mới cho Gapo SlideGen là:

1. Auth đơn giản và identity adapter.
2. Neon database models/repositories.
3. Gemini → OpenAI → OpenAI failover orchestration.
4. API contract gọn cho POC.
5. React renderer với 3–5 layout.
6. Editor state và autosave phù hợp với sản phẩm mới.
