# Gapo SlideGen

POC web app tạo presentation từ prompt theo workflow `prompt -> outline -> slides`.
Repository là monorepo gồm Next.js frontend, FastAPI backend và package contract dùng chung.

## Cấu trúc

```text
gapo-slidegen/
|-- apps/
|   |-- web/                         # Next.js App Router
|   |   `-- src/
|   |       |-- app/                 # Route groups và route-specific UI
|   |       |-- components/          # Shared UI primitives
|   |       |-- lib/                 # API client, env, utilities
|   |       |-- providers/           # Client-only providers
|   |       `-- stores/               # Editor state phản hồi nhanh
|   `-- api/                         # FastAPI
|       |-- app/
|       |   |-- api/                 # HTTP boundary
|       |   |-- auth/                # Identity adapter
|       |   |-- ai/                  # Provider protocol và failover
|       |   |-- core/                # Config, logging
|       |   |-- db/                  # Async SQLAlchemy session
|       |   |-- models/              # ORM models
|       |   |-- schemas/             # Pydantic API/AI schemas
|       |   `-- services/             # Business services
|       |-- alembic/                 # Database migrations
|       `-- tests/
|-- packages/
|   `-- contracts/                   # OpenAPI-generated TypeScript types
|-- docs/
|   `-- architecture.md
|-- .env.example
|-- docker-compose.yml               # PostgreSQL local tùy chọn
`-- SPEC.md
```

Route groups `(auth)`, `(workspace)` và `(present)` tổ chức các layout khác nhau nhưng
không xuất hiện trong URL. Các `_components` là implementation detail của route và
không thể trở thành public route.

## Yêu cầu môi trường

- Node.js 20.9 trở lên và npm 10 trở lên.
- Python 3.11 trở lên.
- PostgreSQL 15 trở lên hoặc Neon PostgreSQL.

## Khởi động frontend

```bash
cp .env.example .env
npm install
npm run dev
```

Mở `http://localhost:3000`. Next.js dùng Neon Auth SDK để quản lý đăng ký, đăng nhập
và HttpOnly session. Các route workspace gọi FastAPI với access token do Neon phát hành.

## Khởi động backend

```bash
cd apps/api
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`. Health check: `GET /health`.

Nếu cần PostgreSQL local:

```bash
docker compose up -d postgres
```

Sau khi cấu hình database:

```bash
cd apps/api
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

`DATABASE_URL` dùng chung cho runtime và Alembic. Với Neon, dùng pooled hostname có
`-pooler`; direct endpoint không cần thiết cho POC này.

### Cấu hình Neon Auth

Trong Neon Console, mở **Auth > Configuration** và chép hai giá trị vào `.env`:

```dotenv
NEON_AUTH_BASE_URL=https://.../auth
NEON_AUTH_JWKS_URL=https://.../.well-known/jwks.json
```

`NEON_AUTH_COOKIE_SECRET` là secret cục bộ của ứng dụng (ít nhất 32 ký tự), không phải
API key của Neon. `NEON_AUTH_ISSUER` và `NEON_AUTH_AUDIENCE` có thể để trống nếu Neon
không cung cấp hai claim này trong cấu hình hiện tại.

Chạy backend và frontend ở hai terminal, rồi mở `http://localhost:3000/sign-up`.
Credentials và session nằm trong schema `neon_auth`; FastAPI chỉ xác minh JWT bằng
JWKS và ánh xạ claim `sub` sang `users`/`user_identities` để giữ ownership nội bộ.

## Kiểm tra chất lượng

```bash
npm run lint
npm run typecheck

cd apps/api
ruff check .
pytest
```

## Đồng bộ contract

FastAPI OpenAPI là nguồn sự thật. Khi API đang chạy:

```bash
npm run contracts:generate
```

Lệnh này ghi TypeScript types vào `packages/contracts/src/generated/api.ts`. Sau khi
generation được đưa vào CI, không chỉnh file generated bằng tay.

## Trạng thái scaffold

- Frontend routes, Neon Auth guard/form, loading/error boundaries và editor state đã có.
- ORM models, Pydantic schemas, API signatures và AI failover policy đã có.
- Neon Auth, JWT/JWKS verification, local ownership mapping và migrations đã có.
- Embedding được cấu hình qua Gemini API; OCR dùng AI vision với OpenAI fallback,
  không yêu cầu model local hay Tesseract.
- Health endpoint và unit tests chạy độc lập với AI provider.
- Presentation CRUD, upload/OCR, SSE và provider SDK adapters còn là milestone tiếp theo.

Chi tiết quyết định kiến trúc nằm trong [docs/architecture.md](docs/architecture.md),
phạm vi sản phẩm nằm trong [SPEC.md](SPEC.md).
