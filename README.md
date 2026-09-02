# Monograph Management System

![checks](https://github.com/USER/REPO/actions/workflows/ci.yml/badge.svg)
<!-- Replace USER/REPO once this is pushed to GitHub. -->

A single place where a university department manages the whole monograph
journey of its final-year students: from the moment a student first proposes
a topic, until the day the finished work is defended, graded and archived.

It replaces the paper, the personal notebooks, the printed drafts and the
WhatsApp messages that this process usually runs on.

---

## What it does

**For students** — one screen showing exactly where they stand. They propose
a topic, see who their supervisor is, upload each draft, read the corrections
they are given, and find their defence date and result. Everything they have
ever submitted stays visible to them.

**For supervisors** — a list of their own students and which ones are waiting
for a response. They read a submission and answer: approve, ask for
revisions, or reject. They can compare an old version against a new one to
check whether their corrections were actually applied.

**For the head of department** — the whole department at once: how many
students are working, how many are stuck, who is behind, and how loaded each
supervisor is. They approve topics, assign supervisors, form committees, set
defence dates, and print the forms the archive needs on paper.

**For committee members** — the monographs they must examine, and where they
enter their score after the defence.

**For the administrator** — accounts, academic years, deadlines, and the
department's own rules.

---

## The journey

Every monograph moves through a fixed sequence and can never skip a stage or
move backwards without a reason being recorded:

```
draft → topic submitted → topic approved → proposal submitted
      → under review ⇄ revision required → proposal approved
      → research in progress → final submission → final review
      → defence scheduled → defended → completed
```

A monograph can also be **rejected** or **withdrawn**, and those endings are
recorded too. The revision loop between *under review* and *revision
required* may repeat as many times as needed; every round is kept.

---

## What makes it survive real use

- **Nothing is ever deleted.** Every version of every file is kept. When a
  student uploads a correction, the previous version stays beside it.
- **Every action is recorded** with who did it and when, in a history nothing
  in the system can rewrite. Arguments about "I submitted on time" and "you
  never gave me corrections" end there.
- **Documents are private.** Files are served only through a permission
  check, never straight off disk. Somebody who may not read a monograph is
  told it does not exist, rather than that they are not allowed.
- **The rules are configuration, not code.** Who approves topics, how
  supervisors are assigned, committee size, grade weights and deadlines all
  differ between departments and are set per department.
- **It prints the paper the archive needs** — topic approval, supervisor
  assignment, defence notice and result sheet — with signature lines ready.
  Without this, staff would type everything twice and stop using the system.
- **It works without internet.** Everything runs on one machine inside the
  university. Only power is needed.
- **It backs itself up** every night, because there is no full-time
  administrator watching it.
- **Login is by student ID, not email.** Many students do not use email.

---

## Running it

**Setting this up for your own department?** Start with
[docs/SETUP-CHECKLIST.md](docs/SETUP-CHECKLIST.md).

For development, see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).
For installing it at a university, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
For the people who will use it, see [docs/USER-GUIDE.md](docs/USER-GUIDE.md).

Quick start, with nothing installed but Python and Node:

```bash
venv/bin/pip install -r backend/requirements.txt
cd backend
../venv/bin/python manage.py migrate
../venv/bin/python manage.py seed_demo     # a department to look at
../venv/bin/python manage.py runserver

cd ../frontend && npm install && npm run dev
```

Open http://localhost:5173 and sign in as `hod001` / `TestPass123!`.

---

## How it is built

**Backend** — Django REST Framework with Channels for live updates, Celery
for the nightly checks, Postgres and Redis in production (SQLite and an
in-memory channel layer in development, so a fresh checkout runs immediately).

**Frontend** — React, Vite and TypeScript, with TanStack Query for data and
Recharts for the charts.

Ten backend apps, grouped by what happens rather than by entity:

| App | Holds |
|---|---|
| `core` | Base models, roles, permissions, the shared error shape |
| `accounts` | People and their roles |
| `organization` | Faculties, departments, years, and each department's rules |
| `monographs` | The record, the workflow engine, and the history |
| `documents` | Uploads, versions, and controlled download |
| `reviews` | Supervisor decisions and written feedback |
| `defenses` | Committees, scheduling, scoring, grades |
| `notifications` | In-app notifications and their delivery |
| `reports` | Dashboards, exports, printable forms |
| `archive` | The permanent library and duplicate-topic checking |

The whole of the workflow lives in one file, `monographs/workflow.py`: all 27
legal moves, who may make each, and what must be true first. Nothing else
writes a monograph's stage, which is why no move escapes the history.

---

## Tests

```bash
cd backend && ../venv/bin/python -m pytest
```

90 tests covering the rules the product depends on: that stages cannot be
skipped, that holding a role is never enough on its own, that a student
cannot see another student's work, and that grades follow the department's
own weights.

---

## Things to know before changing it

- **`recharts` is pinned to 2.15.4 deliberately.** Version 3 mounts its chart
  containers under React 19 but never draws the shapes inside them — every
  chart renders blank, with no error.
- **Chart colours are literal hex values**, not CSS custom properties: SVG
  `fill` does not resolve `var(...)` reliably.
- **`perform_transition` re-reads the row it locks**, so your object is stale
  afterwards. Refresh it, and never save a whole stale instance.
- **Uploaded files must never be served directly by the web server.**

---

## Licence

MIT — see [LICENSE](LICENSE).
