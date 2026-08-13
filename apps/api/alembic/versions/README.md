# Database migrations

Generate the first migration after configuring a PostgreSQL database:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Review every generated migration before applying it. Runtime and migrations use the
pooled Neon connection configured in `DATABASE_URL`.
