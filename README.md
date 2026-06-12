# DocuMind

Ask questions about your own documents and get answers with citations.

Work in progress. Done so far: project skeleton, auth (JWT access tokens with refresh token rotation), workspaces with role-based access, Docker Compose dev environment, CI pipeline. Document ingestion and the RAG chat itself come next.

## Stack

- API: FastAPI, SQLAlchemy (async), PostgreSQL with pgvector, Redis, arq workers
- Web: Next.js, Tailwind CSS
- Infra: Docker Compose, GitHub Actions

## Quick start

Requires Docker.

```
cp .env.example .env    # set a real JWT_SECRET
docker compose up --build
```

- Web: http://localhost:3001
- API docs: http://localhost:8001/docs

Host ports are shifted (3001, 8001, 5433) so the stack coexists with services that commonly sit on the default ports.

## Running tests

Tests need a local Postgres, the compose db service works fine:

```
docker compose up -d db
cd api
python -m venv .venv
.venv/Scripts/activate      # Windows; on Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Layout

```
api/   FastAPI backend: auth, workspaces (ingestion and RAG planned)
web/   Next.js frontend
```
