# Installing the system at a university

Written for whoever installs and looks after this. It assumes one ordinary
server inside the university, and no internet connection once the images are
built.

---

## What you need

- A machine with 4 GB of memory and 40 GB of disk. More disk if the
  department is large: student work accumulates and is never deleted.
- Docker and the Docker Compose plugin.
- A fixed address on the university network.

That is all. No internet connection is required to run it — only to build it
the first time.

---

## Installing

```bash
git clone <the repository> monograph
cd monograph

cp .env.example .env
```

Open `.env` and set these three. Nothing else has to change:

```bash
# Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY=...

POSTGRES_PASSWORD=...

# The address people will type, plus the server's own name
ALLOWED_HOSTS=localhost,monograph.university.edu
UNIVERSITY_NAME=Kabul University
```

`UNIVERSITY_NAME` is printed on the letterhead of every official form, so set
it correctly before anyone prints one.

Then start everything:

```bash
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

Open `http://<the server address>/` — the system is running.

---

## Setting up the department

Sign in to `http://<address>/admin/` as the account you just created.

1. **Faculty** — add the faculty.
2. **Department** — add the department, choose its faculty, and set its head.
   The department's own rules appear on the same page: who approves topics,
   how supervisors are assigned, committee size, grade weights, and how long
   a supervisor may take to respond. **Confirm these with the real head of
   department before anyone starts using the system.**
3. **Academic year** — add the current year and mark it as current.
4. **Research areas** — add the subject areas the department supervises.
5. **Users** — add the head of department, the supervisors, the examiners and
   the students. Students sign in with their student ID.

To try the system before loading real records:

```bash
docker compose exec backend python manage.py seed_demo
```

That creates a department with twelve monographs spread across the stages.
**Never run it on an installation holding real data** — `--wipe` removes
everything.

---

## Backups

The system backs itself up every night at 03:00: the database, and every
uploaded file. They are kept for thirty days.

```bash
docker compose exec backend ls -lh /app/backups
```

**Copy them off this machine regularly.** A backup that lives only on the
disk it is protecting is not a backup. A USB drive, once a week, is enough:

```bash
docker compose cp backend:/app/backups ./backup-$(date +%F)
```

To restore the database from a backup:

```bash
docker compose exec -T db psql -U monograph monograph < backups/db-YYYYMMDD-HHMM.sql
```

---

## Day to day

| Task | Command |
|---|---|
| Is it running? | `docker compose ps` |
| Look at the logs | `docker compose logs -f backend` |
| Restart | `docker compose restart` |
| Stop | `docker compose down` |
| Start again | `docker compose up -d` |
| Health | `curl http://localhost/api/health/ready/` |

The health endpoint reports whether the database and the live-update service
are reachable, which is usually enough to tell what has gone wrong.

---

## After a power cut

Everything restarts on its own — every service is set to `unless-stopped`.
Check that it came back:

```bash
docker compose ps
curl http://localhost/api/health/ready/
```

Postgres survives being switched off suddenly. If a container will not start,
its logs will say why: `docker compose logs backend`.

---

## Upgrading

```bash
git pull
docker compose up -d --build
docker compose exec backend python manage.py migrate
```

Take a backup first. Migrations are applied forwards only.

---

## Serving it over HTTPS

Inside a campus network, plain HTTP is often accepted. If a certificate is
installed in front of the system, set this in `.env` and restart:

```bash
SECURE_SSL_REDIRECT=True
CSRF_TRUSTED_ORIGINS=https://monograph.university.edu
```

---

## When something is wrong

**Nobody can sign in.** Check the backend is up (`docker compose ps`) and
that `ALLOWED_HOSTS` in `.env` includes the address people are typing.

**Uploads fail.** Check the disk: `df -h`. Uploaded work is never deleted, so
the disk fills eventually.

**Dashboards do not update by themselves.** The live-update service needs
Redis: `docker compose ps redis`. The system still works without it — people
just need to reload the page.

**Nightly checks are not running.** They need both the worker and the
scheduler: `docker compose ps worker scheduler`.

---

## Before whoever installed this leaves

The largest risk to this system is not technical. Make sure that:

- Someone at the university knows the `.env` password and where backups go.
- Someone has actually restored a backup once, as practice.
- One enthusiastic teacher in the department knows the system well enough to
  help the others.

A system nobody can maintain stops being used the day its installer leaves.
