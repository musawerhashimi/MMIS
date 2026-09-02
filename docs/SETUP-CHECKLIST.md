# Setting up for your own department

Work through this once, in order. Tick each line as you go.

---

## Before you touch the system

These are questions only your department can answer. Get them settled first,
because they decide how the system behaves and changing them later means
re-explaining it to everyone.

Sit down with the head of department for twenty minutes and write the answers
in the right-hand column.

| Question | Your department's answer |
|---|---|
| Who approves a topic — the head alone, or a committee? | |
| If a committee, how many approvals are needed? | |
| Who chooses the supervisor — the department, the student, or both? | |
| How many students may one supervisor take at once? | |
| How is the final grade split between supervisor and committee? | |
| What is the passing grade? | |
| How many people sit on a defence committee? | |
| How long may a supervisor take to answer a submission? | |
| After how long without progress is a student "stuck"? | |
| May two students write one monograph together? If so, how many at most? | |
| Which forms must be printed and signed on paper? | |

Every one of these is a setting in the system. None of them require a
programmer.

---

## 1. Start the system

```bash
cd backend
../venv/bin/python manage.py migrate
../venv/bin/python manage.py createsuperuser
../venv/bin/python manage.py runserver
```

In a second terminal:

```bash
cd frontend
npm run dev
```

- [ ] `http://localhost:8000/admin/` opens
- [ ] `http://localhost:5173/` opens

---

## 2. Enter your department

Sign in to `http://localhost:8000/admin/` as the superuser you just made.

- [ ] **Faculty** — add yours (name, and a short code such as `CS`)
- [ ] **Department** — add yours, choose the faculty
- [ ] **Department** again — open it and fill in the policy section using
      the answers from the table above
- [ ] **Academic year** — add the current year, tick **is current**
- [ ] **Research areas** — add the subjects your department supervises

---

## 3. Add the people

Still in the admin, or from **People** inside the app once a head of
department exists.

- [ ] The head of department — role **Head of Department**
- [ ] Go back to **Department** and set them as **Head**
- [ ] Each supervisor — role **Supervisor**
- [ ] Each examiner who is not a supervisor — role **Committee Member**
- [ ] Each final-year student — role **Student**, with their student ID

Write each person's password down and give it to them directly. The system
does not send email.

---

## 4. Check it behaves the way your department does

Sign in to `http://localhost:5173/` as the head of department.

- [ ] **Settings** shows your rules, and they match the table above
- [ ] Sign in as a student — they see only their own work
- [ ] The student proposes a topic and submits it
- [ ] The head assigns a supervisor and approves the topic
- [ ] The student uploads a proposal
- [ ] The supervisor requests revisions with a written reason
- [ ] The student sees that feedback
- [ ] **Forms** produces a topic approval form that looks right on paper

If the printed form is wrong, fix `UNIVERSITY_NAME` in the environment before
anyone uses it in earnest.

---

## 5. Put it on the university server

Follow [DEPLOYMENT.md](DEPLOYMENT.md). In short:

- [ ] Docker installed on the server
- [ ] `.env` filled in — `SECRET_KEY`, `POSTGRES_PASSWORD`, `ALLOWED_HOSTS`,
      `UNIVERSITY_NAME`
- [ ] `docker compose up -d --build`
- [ ] `docker compose exec backend python manage.py migrate`
- [ ] The system opens from another computer on the university network
- [ ] A backup has been taken **and restored once**, as practice

---

## 6. Before you hand it over

The requirements warn that the biggest risk to this project is not technical.
It is that nobody keeps it running.

- [ ] One teacher in the department has used the system and likes it
- [ ] That person can add a student account without help
- [ ] Someone other than you knows the `.env` password
- [ ] Someone other than you knows where the backups go
- [ ] [USER-GUIDE.md](USER-GUIDE.md) has been printed or shared

---

## If something is not right

| What you see | What to do |
|---|---|
| A button you expect is missing | Something is not ready — usually a missing file or an unassigned supervisor. The system says which when you try. |
| A department has no settings | `python manage.py backfill_policies` |
| You want to start over with sample data | `python manage.py seed_demo --wipe` — **never on real data** |
| Nothing loads at all | Is the backend running? `curl http://localhost:8000/api/health/` |
