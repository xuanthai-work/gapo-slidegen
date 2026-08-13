# Kiến trúc Gapo SlideGen

## Nguyên tắc phân lớp

```text
Browser
  -> Next.js routes và UI
  -> typed API client
  -> FastAPI routers
  -> business services
  -> SQLAlchemy / AI orchestrator
  -> Neon PostgreSQL / AI providers
```

Next.js không chứa AI provider key hoặc business logic. Frontend chỉ gọi FastAPI qua
JSON API và SSE, luôn gửi session cookie bằng `credentials: include`.

## Next.js App Router

- `src/app` chỉ chịu trách nhiệm routing, layouts, boundaries và route-specific UI.
- `(auth)`, `(workspace)` và `(present)` chọn layout mà không làm thay đổi URL.
- `_components` giữ implementation detail gần route nhưng loại khỏi routing system.
- Shared UI nằm trong `src/components`; API/env utilities nằm trong `src/lib`.
- Server Component là mặc định. Query provider, Zustand editor và tương tác form là
  các Client Component được cô lập.
- `loading.tsx`, `error.tsx` và `not-found.tsx` biểu diễn trạng thái đầy đủ của route.

## FastAPI

- `api`: parse request, response model, status code. Router không chứa business logic.
- `auth`: đổi session/JWT thành `CurrentUser`. Business services không đọc token.
- `services`: ownership query và transaction boundary.
- `ai`: provider protocol, error taxonomy, retry budget và ordered failover.
- `schemas`: dữ liệu tại API/AI boundary luôn qua Pydantic validation.
- `models`: persistence model, JSONB chỉ chứa dữ liệu đã validate.

Mọi resource query phải chứa cả resource ID và `owner_id`. UUID từ client không đủ để
chứng minh quyền truy cập.

## Contract

FastAPI OpenAPI là nguồn sự thật. `openapi-typescript` sinh types cho frontend vào
`packages/contracts`. Những type viết tay hiện tại chỉ phục vụ scaffold và nên được
thay dần bằng generated types.

## Generation và SSE

Generation job phải được ghi database trước khi chạy. Event tối thiểu:

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

Mỗi event chứa `job_id`, timestamp, progress và payload. Reconnect không phụ thuộc vào
memory của process; client đọc lại snapshot job rồi tiếp tục stream.

## AI failover

`AIOrchestrator` nhận một ordered provider chain. Timeout, 429, lỗi mạng, 5xx và output
không validate có thể retry/failover trong budget. Invalid request, policy refusal,
sai API key và lỗi lập trình phải dừng ngay.

Log metadata gồm request ID, job ID, provider, model, attempt, latency và failure kind.
Không log API key, cookie, password hoặc toàn bộ prompt ở production.

## Milestone tiếp theo

1. Hoàn thiện auth session, CSRF và rate limit.
2. Tạo migration đầu tiên và CRUD có ownership test.
3. Cài Google/OpenAI provider adapters, structured output và metrics.
4. Persist generation job, triển khai SSE reconnect.
5. Nối frontend forms/query hooks và thay dữ liệu trình diễn.
6. Thêm component tests và E2E happy path.
