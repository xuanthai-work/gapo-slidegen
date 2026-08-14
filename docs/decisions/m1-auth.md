# M1 internal authentication

Status: implemented; live PostgreSQL migration check pending

## Scope

The MVP supports internal accounts with email and password. Email addresses are
syntax-validated and normalized, but mailbox or domain deliverability is not
checked and no verification email is sent.

This is intentionally a replaceable local auth boundary. It does not assume
the future company identity system, domain restrictions, SSO protocol, or user
directory shape.

## Session design

- Passwords are hashed with Argon2 through `pwdlib`.
- Login creates a cryptographically random opaque token.
- Only the SHA-256 token digest is stored in PostgreSQL.
- The raw token is sent in an HttpOnly, SameSite=Lax cookie.
- Cookies are marked Secure in the production environment.
- Sessions expire after seven days by default and can be revoked immediately.
- Logout is idempotent and deletes the browser cookie.

Opaque server-side sessions were chosen over JWTs because account count is
small, immediate revocation is useful, and a future company auth integration
can replace the session issuer without changing presentation ownership.

## Ownership

`source_records.owner_id` and `generation_jobs.owner_id` now reference
`users.id` with cascading deletion. Repository reads filter by both object id
and owner id. Ingestion endpoints require an authenticated user.

The `/v1/sources` endpoints persist normalized content and raw uploads under
the authenticated owner. The lower-level `/v1/ingestion` endpoints remain as
authenticated extraction previews.

## Local database

`compose.yaml` pins the official `postgres:18.4-alpine3.24` image. The local
credentials are development-only and match `.env.example`.

Start and migrate with:

```bash
npm run db:up
npm run db:migrate
```

The compose configuration validates and all migrations compile to PostgreSQL
DDL. A live migration was not run because Docker Desktop was not running on the
development machine at verification time.

## Verification

- Password verification and opaque token hashing tests pass.
- Email normalization works without deliverability checks.
- Register, login, current-user, and logout HTTP contracts pass.
- Login sets HttpOnly session cookies and logout clears them.
- Unauthenticated ingestion returns HTTP 401.
- Migration 0002 creates users/sessions and ownership foreign keys.

## Web integration

Next.js proxies `/api/backend/*` to FastAPI using
`SLIDEGEN_API_INTERNAL_URL`. This keeps browser requests same-origin and lets
the HttpOnly cookie work without exposing the API address to client code.

The web application includes register/login, current-session loading, logout,
and an authenticated dashboard. Registration immediately signs the new user
in; it does not verify the mailbox.
