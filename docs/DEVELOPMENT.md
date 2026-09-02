# Running the system locally

## First time

```bash
# Backend dependencies (the virtualenv lives at the repo root as `venv/`)
venv/bin/pip install -r backend/requirements.txt

# Database — SQLite by default, no server needed
cd backend
../venv/bin/python manage.py migrate
../venv/bin/python manage.py createsuperuser

# A department with twelve monographs across the stages, so every screen
# has something on it.
../venv/bin/python manage.py seed_demo

# Frontend dependencies
cd ../frontend
npm install
```

## Every day

Two terminals:

```bash
# Terminal 1 — API on :8000
cd backend && ../venv/bin/python manage.py runserver

# Terminal 2 — app on :5173
cd frontend && npm run dev
```

Open http://localhost:5173. Vite proxies `/api` and `/ws` to the backend, so
the browser sees a single origin and there is no CORS to configure.

## Using Postgres and Redis instead

Development defaults to SQLite and an in-memory channel layer so the project
runs with nothing installed. To match production locally, set these in
`backend/.env`:

```
USE_POSTGRES=True
USE_REDIS=True
```

Redis is required for real-time updates across more than one server process
and for the scheduled jobs.

## Background jobs

The nightly deadline checks and backups run under Celery:

```bash
cd backend
../venv/bin/celery -A config worker -l info      # runs the tasks
../venv/bin/celery -A config beat -l info        # triggers them on schedule
```

In development `CELERY_TASK_ALWAYS_EAGER` is on, so tasks run inline and
neither process is needed unless you are testing the schedule itself.

## Tests

```bash
cd backend && ../venv/bin/python -m pytest
```

88 tests, about fourteen seconds, against an in-memory database — no Postgres
needed. They cover the workflow rules, permissions, document versioning,
grade calculation and access isolation.

Run one file while working on it:

```bash
../venv/bin/python -m pytest monographs/tests.py -q
```

## Notes for whoever works on this next

- **`recharts` is pinned to 2.15.4 on purpose.** Version 3 mounts its chart
  containers under React 19 but never draws the shapes inside them — the DOM
  shows empty `recharts-shape` groups and every chart renders blank. Do not
  upgrade without checking a chart actually appears.
- **Chart colours are literal hex values**, not CSS custom properties. SVG
  `fill` does not resolve `var(...)` reliably.
- Uploaded files are served only through a permission-checked view. Never
  point the web server at `private_media/` directly.
- **`perform_transition` re-reads the row it locks**, so your local object
  is stale once it returns. Refresh it, and never `save()` a whole stale
  instance afterwards — that writes the old stage back over the new one.
