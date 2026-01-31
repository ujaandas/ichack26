# Hackathon Starterkit Backend

This directory contains the FastAPI backend for the project. It is structured to be simple, modular, and easy to extend. The backend exposes a typed OpenAPI schema that the frontend consumes through HeyAPI‑generated clients.

---

# Overview

The backend is organized into **feature modules** (`auth/`, `users/`, etc.).
Each module follows the same pattern:

- `models.py` — Pydantic models / ORM models
- `routes.py` — API endpoints
- `service.py` — business logic
- `dependencies.py` — shared dependencies (optional)

This keeps logic separated and easy to scale.

---

# Running the Backend

The backend is normally run through Docker Compose (inside `infra/`):

```sh
cd infra
docker compose up --build
```

The API will be available at:

```sh
http://localhost:8000
```

Interactive docs:

```sh
http://localhost:8000/docs
```

---

# Configuration

Configuration lives in `app/config.py`.
Environment variables are passed in via Docker Compose.

Typical settings include:

- database URL
- environment mode
- secrets / tokens (if needed)

---

# Database

Database

`app/database.py` defines:

- SQLAlchemy engine
- session factory
- dependency for request‑scoped sessions

If you add new models, ensure they are imported somewhere during startup so SQLAlchemy can register them.

---

# Adding a New Feature

To add a new domain/module (e.g., `posts`):

1. Create a folder:

```sh
backend/app/posts/
```

2. Add the standard files:

```sh
# models.py
# routes.py
# service.py
# dependencies.py (optional)
```

3. Register the router in `main.py`:

```sh
from app.posts.routes import router as posts_router
app.include_router(posts_router, prefix="/posts")
```

4. Restart the backend container.

This pattern keeps the codebase modular and predictable.

> ### Updating the API Client
>
> Whenever you change backend routes, regenerate the HeyAPI client:
> `pnpm run openapi`
> This keeps the frontend fully typed and in sync with the backend.
