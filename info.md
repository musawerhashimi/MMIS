# This is my old project struchter as you can see

Root

SchollProject/
├── backend/ # Django REST API
├── frontend/ # React + Vite + TS
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── .env / .env.example
├── .dockerignore
├── .gitignore
└── railpack-plan.json
Backend (Django)

backend/
├── manage.py
├── requirements.txt
├── school/ # Django project (settings, urls, wsgi)
├── core/ # shared/base app
├── accounts/ # auth & users
├── academic/ # academic years, classes
├── students/
├── staff/
├── teachers/ (within staff)
├── parents/
├── assignment/
├── exam/
├── fees/
├── library/
├── messaging/
├── cms/ # public site content
├── prompts/
├── media/ # uploaded files
└── staticfiles/

# Each Django app follows:

<app>/
├── **init**.py
├── apps.py
├── admin.py
├── models.py
├── serializers.py
├── views.py
├── urls.py
├── filters.py
├── tests.py
├── services/ # business logic
├── management/commands/ # CLI commands
└── migrations/
Frontend (React + Vite + TypeScript)

frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
├── eslint.config.js
├── public/
│ └── images/{events,news}/
└── src/
├── main.tsx, App.tsx
├── assets/
├── components/layout/ # public site layout
├── pages/ # public site pages
│ ├── Home/ About/ Academic/ Achievements/
│ ├── Careers/ Community/ Contact/
│ ├── Media/ StudentsActivities/
├── constants/ data/ entities/
├── hooks/ lib/ utils/
├──
├── providers/ queries/ services/ stores/
├── schemas/ types/
└── mis/ # MIS (admin) sub-app
├── components/
├── data/
├── hooks/
├── lib/
├── locales/ # en, da, pa, ...
├── providers/
├── queries/
├── services/
├── routes.tsx
└── modules/ # feature modules
├── auth/ (api, components, hooks, pages, schemas, stores)
├── dashboard/
├── academic/ (components, hooks, pages, schemas, services)
├── students/ (+ utils)
├── staff/
├── teachers/ (+ utils)
├── parents/
├── assignment/
├── exam/ (+ utils)
├── library/
├── messaging/ (+ stores, types)
├── cms/
============================
but now i want to create a new project that have this information as you can see i want to create this project step by step if you have any question you are free to ask me

-the frontend MIS or Dashborad

- make this project profitnal ui , amazing , and user frienly not be simple
- real time process when neded every where
- use Some js graph or circle shapes and etc
  -if you have question ask
  ==============================info of new project============

# University Monograph Management System

### Project Description Document

---

## 1. What This Project Is

A single online system where a university department manages the entire monograph journey of its final-year students — from the moment a student first proposes a topic, until the day the finished monograph is defended, graded, and archived.

Today most departments handle this on paper, in personal notebooks, through printed drafts, and over phone calls and WhatsApp messages. Files get lost. Nobody knows how many students are behind schedule. A supervisor cannot remember which version of a chapter he already corrected. The department head has no clear picture until the very end of the year, when it is too late to fix anything.

This system replaces all of that with one organized place that everyone shares.

---

## 2. The Problems It Solves

**Nobody knows where anyone is.** The department head cannot answer a simple question like "how many students have finished their proposal?" without calling every supervisor one by one.

**Documents get lost or confused.** A student sends chapter two by email, then sends a corrected version by WhatsApp, then hands a printed copy to the supervisor. Three versions now exist and nobody is sure which one is the real one.

**Feedback disappears.** A supervisor writes corrections on a printed page. The page is lost. Six weeks later there is an argument about whether the corrections were ever given.

**Deadlines pass silently.** A student stops working for two months and nobody notices until the defense season arrives.

**Supervisors are unevenly loaded.** One popular professor ends up with twenty-five students while another has three. Nobody planned it, it just happened.

**Topics get repeated.** Two students in the same year write about the same subject, or a student unknowingly repeats a monograph written three years earlier, because there is no searchable record of past work.

**There is no record afterwards.** Once the students graduate, their monographs sit in a cupboard. Nobody can search them, read them, or learn from them.

---

## 3. Who Uses The System

**Students** — final-year students who must write and defend a monograph to graduate.

**Supervisors** — the teachers who guide students, read their drafts, give corrections, and approve their work.

**Head of Department** — the person who approves topics, assigns supervisors to students, schedules defenses, and watches over the whole department's progress.

**Defense Committee Members** — teachers who attend the defense, ask questions, and give scores.

**Administrator** — the person who manages the system itself: creating accounts, setting up the academic year, and keeping records in order.

---

## 4. What Each Person Does In The System

### The Student

Logs in and sees one screen showing exactly where they stand. They propose their topic, wait for approval, learn who their supervisor is, upload their proposal, read the corrections their supervisor writes, upload corrected versions, upload each chapter as they finish it, upload the final monograph, and finally see their defense date, location, and result. Everything they have ever submitted and every comment they have ever received stays visible to them permanently.

### The Supervisor

Logs in and sees a list of their own students and which ones are waiting for a response. They open a student's submission, read it, and choose one of three answers: approve it, ask for revisions, or reject it. When they ask for revisions they write down exactly what needs to change, and the student sees it immediately. They can also compare an old version with a new one to check whether their corrections were actually applied.

### The Head of Department

Logs in and sees the whole department at once: how many students are working, how many are stuck, who is behind schedule, and how loaded each supervisor is. They approve or reject proposed topics, assign supervisors to students, form defense committees, set defense dates, and print official forms when the university archive needs paper copies.

### The Committee Member

Sees the monographs they must examine before the defense day, reads them in advance, and enters their score and comments after the defense.

### The Administrator

Creates and manages accounts, opens and closes academic years, sets the deadlines for each stage, and produces reports for the faculty.

---

## 5. The Journey Of A Monograph

This is the heart of the project. Every monograph moves through a fixed series of stages, and it can never skip a stage or move backwards without a reason being recorded.

**Stage 1 — Draft.** The student writes down their idea: a working title, the research area, and what they want to achieve. Nothing is official yet and the student can change anything freely.

**Stage 2 — Topic Submitted.** The student formally submits the topic to the department. It is now locked and waiting for a decision.

**Stage 3 — Topic Approved.** The department head reviews the topic, checks that it is suitable and that no other student is doing the same thing, and approves it. At this moment a supervisor is assigned to the student. If the topic is not suitable it goes back to the student with an explanation.

**Stage 4 — Proposal Submitted.** The student writes a full research proposal — objectives, methodology, expected outcome — and submits it to their supervisor.

**Stage 5 — Under Review.** The supervisor is reading the proposal. The student can see that it is being reviewed and is not left wondering.

**Stage 6 — Revision Required.** If the supervisor is not satisfied, the proposal comes back with written corrections. The student fixes it and submits again. This loop can repeat as many times as needed, and every round is recorded.

**Stage 7 — Proposal Approved.** The supervisor is satisfied. The research is officially allowed to begin.

**Stage 8 — Research In Progress.** The student is now doing the actual work and uploading chapters one by one as they are completed. Each chapter is reviewed the same way as the proposal was.

**Stage 9 — Final Submission.** The student uploads the complete finished monograph.

**Stage 10 — Final Review.** The supervisor reads the whole work and decides whether the student is ready to defend. If not, it goes back for revision.

**Stage 11 — Defense Scheduled.** The department head sets the date, time, and place, and appoints the committee. Everyone involved is notified.

**Stage 12 — Defended.** The defense has taken place. Each committee member enters their score and comments. The result is recorded: passed, passed with minor revisions, or failed.

**Stage 13 — Completed.** The final approved copy is archived, the final grade is recorded, and the monograph becomes part of the department's permanent searchable library.

A monograph can also be **rejected** or **withdrawn** at certain points, and those endings are recorded too.

---

## 6. What The System Keeps

### About each monograph

The title in both Dari and English, the abstract, the research area, the objectives, the methodology, the keywords, who the student is, who the supervisor is, which department and which academic year it belongs to, what stage it is currently in, and the dates it entered each stage.

### About each document

Every file a student uploads is kept forever — the proposal, each chapter, the final monograph, the defense presentation, and any supporting material. Nothing is ever deleted. When a student uploads a corrected version, the old version is kept beside it as version one, version two, version three, and so on. The system records who uploaded each file and exactly when.

### About each review

Every decision a supervisor makes — approve, reject, or request revision — is saved together with the written comments, the date, and which version of the document it referred to.

### About each defense

The date, time, place, the names and roles of every committee member, the score each one gave, their comments, the overall result, and the final grade.

### A complete history

Every single action taken on a monograph is written into a permanent history that can never be edited or erased. Who did what, and when. This means arguments about "I submitted it on time" or "you never gave me corrections" simply end — the record is there for both sides to see.

---

## 7. What The System Shows

### For the head of department

How many students are working this year. How many are at each stage. How many are waiting for their supervisor to respond. How many are behind their deadline. How many students each supervisor is carrying and whether anyone is overloaded. How long students are typically spending at each stage — which immediately shows where the department's real bottleneck is.

### For the supervisor

Which of their students are waiting for a response right now. What was recently submitted. Which students have gone quiet and are falling behind.

### For the student

Their current stage, their supervisor's name, all the feedback they have received, all the documents they have submitted, their upcoming deadline, and their defense details once scheduled.

### Reports the department can print or export

Progress report for the whole year. List of students behind schedule. Supervisor workload report. Defense results and final grades. A yearly summary for the faculty.

---

## 8. Features That Make It Fit An Afghan University

**Works in Dari, Pashto, and English.** The whole interface is available in all three, written right-to-left where it should be.

**Uses the Shamsi calendar.** All dates are shown as students and teachers actually read them.

**Prints official forms.** Universities still need paper with signatures for the archive. The system produces the topic approval form, the supervisor assignment letter, the defense notice, and the defense result sheet — properly formatted, in the right language, with signature lines ready. Without this, staff would have to type the same information twice and the system would be abandoned.

**Works without internet.** The system can run on a computer inside the university itself, so it keeps working when the internet is down. Only power is needed.

**Works on cheap phones and slow connections.** Most students will open it on a mobile phone with weak signal, so it must stay light and fast.

**Does not depend on email.** Many students do not use email regularly. Login is by student ID, and notifications appear inside the system itself.

**Keeps its own backups.** Copies of everything are saved automatically every night, so a failed hard disk does not destroy four years of student work.

---

## 9. What Is Not Included

Being clear about the limits keeps the project finishable.

The system does not manage courses, class attendance, exam marks, or fees — it is only about monographs. It does not check for plagiarism against the whole internet; it only checks whether a topic is similar to previous monographs in the same department. It does not write or edit documents inside the system; students write in Word and upload the file. It does not replace face-to-face supervision meetings — it records and organizes them, it does not do the teaching.

---

## 10. Suggested Order Of Work

**First, the foundation.** Accounts, roles, departments, academic years, and the basic screens in all three languages.

**Second, the journey.** The complete stage-by-stage flow from draft to completed, with the permanent history. This is the spine of the whole project and everything else attaches to it. It should be finished and working before anything else is started.

**Third, the documents.** Uploading, version keeping, and safe downloading that only the right people can access.

**Fourth, the reviews.** Supervisor decisions and written feedback going back to students.

**Fifth, the defense.** Committees, scheduling, scoring, and final grades.

**Sixth, the dashboards and reports.**

**Seventh, the extras.** Printable forms, notifications, and duplicate topic checking.

**Last, putting it into real use.** Installing it at the university, loading real student and teacher information, training the staff, and writing a simple user guide in Dari.

---

## 11. Risks To Plan For

**Staff may not want to use it.** This is the biggest risk by far, bigger than any technical problem. Older teachers may prefer paper. The answer is to make the system produce the paper they need, keep the screens extremely simple, and train one enthusiastic teacher in each department who then helps the others.

**The process may differ from what you assume.** Every university and even every department has slightly different rules about who approves topics and how grades are weighted. These must be confirmed with a real department head before the work is designed, not after.

**Power and internet interruptions.** The system must survive being switched off suddenly without losing data.

**Nobody to maintain it after you.** Write documentation and train at least one person at the university, otherwise the system dies the day you leave.

**Growing the project too big.** It is tempting to add attendance, exams, fees, and a library. Resist it. A finished monograph system that people actually use is worth far more than a huge unfinished one.

---

## 12. Why It Is Worth Building

For students, it removes the confusion and anxiety of not knowing where they stand and whether their work has been received.

For supervisors, it removes the mess of scattered files and forgotten corrections.

For the department, it turns an invisible process into a visible one that can finally be measured and improved.

For the university, it creates something that did not exist before: a permanent, searchable archive of the research its students have produced — which future students can learn from instead of starting from nothing every year.

---

## 13. Questions To Confirm Before Starting

1. Who approves a student's topic — one department head, or a committee?
2. Who chooses the supervisor: the student, the department, or both together?
3. How many students is one supervisor allowed to take at a time?
4. How is the final grade calculated — how much comes from the supervisor and how much from the committee?
5. How many people sit on a defense committee, and what are their roles?
6. Are there fixed deadlines for each stage, or does each supervisor set their own?
7. Which official forms must be printed and signed on paper?
8. Do students work alone, or can two students share one monograph?
9. Will the system be used by one department first, or the whole faculty from the start?
10. Who at the university will maintain the system after it is delivered?

==================================================================
