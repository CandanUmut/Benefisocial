# BenefiSocial — Platform & API Documentation (MVP)

## 0) TL;DR

* **What it is:** A helping-focused social platform where people and teams share best practices, ask questions, form projects, match helpers to needs (RFH), run events, and rate usefulness.
* **Stack:** Supabase (Auth, DB, Storage) + Postgres (RLS) + FastAPI (Python) + SQLAlchemy Async + Flutter (web/mobile) + HTTP bearer (Supabase JWT).
* **MVP status:** Auth end-to-end working; DB schema + RLS deployed; core APIs online (profiles, RFH, matching, content, Q\&A, projects, events, ratings/views); Flutter app signs in with GitHub/Google via Supabase; lists + detail + create flows; basic rating & view tracking; modernized UI scaffolds.
* **Next big steps:** Image uploads (profile & post attachments), richer feed (sort by “helpfulness”), pagination & search, moderation tools, agent assistant, and polished UX.

---

## 1) Vision & Context

**BenefiSocial** is a trustworthy, community-driven space for:

* Sharing **best practices**, guides, stories, case studies.
* **Asking/answering** questions with evidence levels.
* Creating **help requests (RFH)** and matching helpers to needs.
* **Collaborating** in projects, team formation, mentorship.
* Hosting **events** (courses/webinars/workshops).
* Lightweight **ratings** (“stars”), **views**, and **reputation**.
* An eventual **AI Agent** that helps with triage, moderation, search, and matching (with “AI-labeled” entries when it creates content).

Design goals:

* **Credible & safe:** RLS, fine-grained policies, audit-friendly metrics.
* **Low friction:** OAuth only; no password DB.
* **Composable:** Single “entity” patterns (ratings/views/comments), tags, unified feed.
* **Scalable:** Supabase-managed Postgres, storage, and JWKS-based JWT auth.

---

## 2) Architecture Overview

**Clients**

* Flutter app (Web + Mobile): Supabase OAuth, calls backend with `Authorization: Bearer <access_token>`.

**Server**

* FastAPI (`/api`): Stateless API, validates Supabase JWT using JWKS; talks to Postgres via SQLAlchemy Async + asyncpg.

**Data / Infra**

* Supabase:

  * **Auth**: OAuth providers (GitHub, Google) via Supabase.
  * **DB**: Postgres + Extensions (uuid-ossp, pgcrypto, pg\_trgm, unaccent).
  * **Storage**: Buckets for profile images and content attachments.
  * **RLS**: Row-level security policies for privacy & role-based operations.

**Security**

* JWT verification using **JWKS** (Supabase `.../auth/v1/keys`).
* RLS across tables.
* CORS restricted to known origins for browsers.

---

## 3) Local Dev Setup

### 3.1 Backend

**Requirements**

* Python 3.11+
* `poetry` or venv + pip
* Supabase project with DB & Auth configured

**Install**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
```

**Environment (.env)**

```env
# App
APP_NAME=BenefiSocial
API_PREFIX=/api
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173

# Database (asyncpg)
# Use the Supabase connection string but convert to asyncpg and keep SSL relaxed locally
DATABASE_URL=postgresql+asyncpg://postgres:<YOUR-DB-PASSWORD>@db.<PROJECT-REF>.supabase.co:5432/postgres
DB_SSL_MODE=relax   # 'require' on prod; 'relax' fixes Windows/local cert issues

# Supabase Auth (JWT)
SUPABASE_PROJECT_URL=https://<PROJECT-REF>.supabase.co
SUPABASE_JWKS_URL=https://<PROJECT-REF>.supabase.co/auth/v1/keys
# optional: SUPABASE_AUDIENCE=authenticated  (default works; keep if needed)
```

**Run**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Health: http://localhost:8000/api/healthz
```

### 3.2 Flutter

**Requirements**

* Flutter SDK (stable)
* `supabase_flutter`, `go_router`, `http`, `file_picker`, `file_picker_web` in `pubspec.yaml`

**Config (`lib/config.dart`)**

```dart
const SUPABASE_URL = "https://<PROJECT-REF>.supabase.co";
const SUPABASE_ANON_KEY = "<YOUR-ANON-PUBLIC-KEY>";
const BACKEND_BASE_URL = "http://localhost:8000";
const API_PREFIX = "/api";
```

**Run Web**

```bash
flutter run -d chrome
# GitHub OAuth callback in Supabase: https://<PROJECT-REF>.supabase.co/auth/v1/callback
```

---

## 4) Environment Variables (Reference)

| Var                       | Where   | Example                                                              | Notes                            |
| ------------------------- | ------- | -------------------------------------------------------------------- | -------------------------------- |
| `APP_NAME`                | backend | `BenefiSocial`                                                       | Branding                         |
| `API_PREFIX`              | backend | `/api`                                                               | Router prefix                    |
| `CORS_ORIGINS`            | backend | `http://localhost:3000,...`                                          | Comma-separated                  |
| `DATABASE_URL`            | backend | `postgresql+asyncpg://postgres:...@db.ref.supabase.co:5432/postgres` | Use `+asyncpg`                   |
| `DB_SSL_MODE`             | backend | `relax`                                                              | `require` on prod; `relax` local |
| `SUPABASE_PROJECT_URL`    | backend | `https://...supabase.co`                                             | For reference/logs               |
| `SUPABASE_JWKS_URL`       | backend | `https://.../auth/v1/keys`                                           | **Use /keys (not well-known)**   |
| `SUPABASE_AUDIENCE` (opt) | backend | `authenticated`                                                      | If you enforce aud               |
| `SUPABASE_URL`            | flutter | `https://...supabase.co`                                             | Public                           |
| `SUPABASE_ANON_KEY`       | flutter | `eyJ...`                                                             | Public anon key                  |
| `BACKEND_BASE_URL`        | flutter | `http://localhost:8000`                                              | Backend URL                      |
| `API_PREFIX`              | flutter | `/api`                                                               | Keep in sync                     |

---

## 5) Database Model (Highlights)

**Core tables**

* `profiles` (linked to `auth.users(id)`) — username, bio, avatar\_url, roles, offers/needs tags, reputation.
* `tags` — slug/label.
* `content` + `content_tags` — best practices, guides, stories, materials…
* `questions`, `answers` — Q\&A with visibility & evidence/sources.
* `rfh` — Requests for Help. `rfh_public` view masks requester if anonymous (except owner/admin).
* `rfh_matches` — helper suggestions/scores.
* `mentorship` — mentor/mentee pairs.
* `projects`, `project_members`, `project_applications`.
* `events`, `event_enrollments`.
* `discussion_topics`, `forum_posts`.
* `comments` — polymorphic comments via entity\_kind + entity\_id.
* `ratings` — unified 1–5 stars for any entity\_kind.
* `views` — pageview-like records for any entity\_kind.
* `notifications`, `reports`, `badges`, `user_badges`.
* `feed_union` view — union of content, questions, projects, rfh for simple feed.

**Extensions**

* `uuid-ossp`, `pgcrypto`, `pg_trgm`, `unaccent`.

**RLS**

* Strict per-table policies (owner-only insert/update where needed; public read where safe; admin/mod overrides).

---

## 6) Auth & Security

**Auth flow**

* Flutter → Supabase OAuth (PKCE for web).
* Supabase returns session + `access_token`.
* Flutter adds `Authorization: Bearer <access_token>` header on backend calls.
* Backend **does not call Supabase** to verify tokens; it verifies signature with **JWKS** (`/auth/v1/keys`) and extracts `sub` (user id).
* Backend enforces authorization + RLS enforces data-level access.

**Common gotchas**

* Callback URL mismatch → OAuth fails (server\_error “Unable to exchange external code”). Fix provider config (GitHub/Google) to Supabase callback.
* Windows local SSL errors to DB → use `DB_SSL_MODE=relax`.

---

## 7) API Reference (MVP)

Base: `http://<backend-host>:8000/api`

### Health

* `GET /healthz` → `{ "status": "ok" }`

### Profiles

* `GET /profiles/me` (auth) → your profile
* `PUT /profiles/me` (auth) → update profile (bio, avatar\_url, languages, offers/needs, …)

**Example**

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/profiles/me
```

### RFH (Request for Help)

* `POST /rfh` (auth)

  * body: `{ title, body, tags[], sensitivity, anonymous, region?, language? }`
  * returns: `{ id }`
* `GET /rfh` (public) — list (optional `?q=&tag=`). Returns (when available): `views`, `avg_stars`, `ratings_count`.
* `GET /rfh/{id}` (public/owner) — masked if anonymous & not owner/admin.

  * includes metrics when present (`views`, `avg_stars`, `ratings_count`) and `is_owner` boolean.
* `DELETE /rfh/{id}` (auth owner) — delete own request.

**Matching**

* `GET /match/{rfh_id}` (auth) — top helpers by overlapping tags + reputation.

**Example**

```bash
curl -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Need help with detox","body":"…","tags":["addiction","mentoring"],"sensitivity":"normal","anonymous":true,"language":"tr"}' \
  http://localhost:8000/api/rfh
```

### Content (Best Practices / Guides / Stories / Materials)

* `POST /content` (auth):

  * `{ type, title, summary?, body?, evidence?, visibility?, region?, language?, tags[] }`
  * auto-creates new tags if missing and links via `content_tags`.
* `GET /content` (public) — list `?q=&tag=`
* `GET /content/{id}` (public/owner/admin)

### Q\&A

* `POST /qa/questions` (auth)

  * `{ title, body?, tags[], visibility, sources? }`
* `GET /qa/questions` (public) — list (`?q=&tag=`) with metrics.
* `GET /qa/questions/{qid}` (public or owner) — with metrics.
* `DELETE /qa/questions/{qid}` (auth owner) — delete own question.
* `POST /qa/answers` (auth)

  * `{ question_id, body, evidence?, sources? }`
* `GET /qa/questions/{qid}/answers` (public)
* `POST /qa/questions/{qid}/accept/{aid}` (auth owner) — accept answer.

### Projects

* `GET /projects` (public/member/owner per RLS)
* `POST /projects` (auth owner)
* `POST /projects/{id}/apply` (auth) — apply to join.

### Events

* `GET /events` (public/host)
* `POST /events` (auth host)
* `POST /events/{id}/enroll` (auth) — RSVP.

### Ratings & Views (Unified)

* `POST /ratings` (auth) — rate any entity.

  * `{ entity: 'rfh'|'question'|'content'|..., entity_id: uuid, stars: 1..5 }`
* `POST /metrics/view` (auth optional) — record a view.

  * `{ entity: 'rfh'|'question'|..., entity_id: uuid }`

> The Flutter app already calls `addView('rfh', id)` and `rate('rfh', id, stars)` through `ApiClient`.

### Notifications, Reports (Optional in MVP)

* `GET /notifications` (auth)
* `POST /reports` (auth)

> If a route file is absent, it’s skipped automatically by the API router.

---

## 8) Flutter App (MVP)

**Key pieces**

* `main.dart`: Supabase initialize (web uses PKCE), Material3 theme, router.
* `routes.dart`: GoRouter with auth-aware redirect.
* `screens/…`:

  * **Auth**: Sign-in screen (GitHub/Google).
  * **HomeShell**: Bottom/side navigation, FABs for create flows.
  * **RFH**: list / detail (with star rater + helper matches) / create.
  * **Q\&A**: list / create question / answers list; delete & accept owned.
  * **Content**: list / create.
  * **Projects & Events**: basic list/create flows.
* `services/api_client.dart`: Handles token headers & REST calls.
* `widgets/common.dart`: `AppScaffold`, `Loading`, `Empty`, common UI helpers.
* **Theme**: Material 3, rounded shapes, modern cards, segmented controls.

**Auth routing**

* If session is null → redirect to `/signin`.
* After OAuth returns, Supabase handles the deeplink and stores session; router refreshes.

---

## 9) Images / File Uploads

**Strategy**

* Use **Supabase Storage** bucket(s):

  * `avatars` (public read) → store profile images.
  * `attachments` (public read or signed URLs) → content/RFH/Q\&A attachments.
* Flutter: integrate `file_picker`/`file_picker_web` to pick files.
* Upload directly to Supabase Storage using `supabase.storage.from('attachments').upload(...)`.
* Save the **public URL** (or signed URL) in the appropriate record:

  * For content/Q\&A: store in `sources` JSON array or a `media` field if you add one.
  * For profile: store URL in `profiles.avatar_url`.

**Backend**

* No need to proxy uploads at MVP (client → Supabase directly).
* If you want validations/virus scan later, add a backend signed upload URL endpoint.

---

## 10) Scoring / Rankings (MVP)

* **Views** & **Ratings** collected uniformly (entity\_kind + id).
* “Helpful” sort can be computed client-side for now (newest with a light freshness boost), or server-side later:

  * e.g. `score = log(views + 1) * (avg_stars * ratings_count)` with time decay.
* `feed_union` can power a basic homepage.

---

## 11) Roadmap

**Short-term (MVP polish)**

* [ ] **Images**: Profile avatar upload + attach images to RFH/Q\&A/Content.
* [ ] **Metrics in list endpoints**: add joins for `views`, `avg_stars`, `ratings_count` consistently to RFH/Content/Projects/Events.
* [ ] **Pagination & search**: `limit/offset` + text search using `tsvector` and `pg_trgm`.
* [ ] **Usernames**: join `profiles` in list/details to display `username` instead of raw UUID.
* [ ] **Better errors**: consistent error shape `{error, detail, code}`.
* [ ] **CI/format**: Ruff + Black + mypy; Flutter lints; pre-commit.

**Mid-term**

* [ ] **Moderation**: reporting flows, admin UI, soft-deletes, shadow bans.
* [ ] **Mentorship**: match mentor/mentee with preferences & schedules.
* [ ] **Direct messaging** or Slack/Discord bridge; later WebRTC.
* [ ] **Notifications**: digest emails, push for mobile/web.
* [ ] **Reputation**: badge triggers, upweight mentors, downweight low-signal.
* [ ] **Agent**: platform-specific AI assistant for triage/search/matching; “AI-labeled posts”; feedback loop for tuning.

**Long-term**

* [ ] **Decentralization**: AdilNet/TimeCoin experimentation; export/import profiles/content.
* [ ] **Org spaces**: multi-tenant groups, custom policies, data residency.
* [ ] **Analytics**: impact dashboards (reach, collaborations).
* [ ] **Monetization**: grants, donations, sponsorship for verified initiatives.

---

## 12) Testing & Examples

**Auth test (backend)**

```python
# tests/dev_bearer_ping.py
import os, httpx
BASE = os.getenv("BASE","http://localhost:8000/api")
TOKEN = os.getenv("TOKEN")  # paste a Supabase access_token
r = httpx.get(f"{BASE}/profiles/me", headers={"Authorization": f"Bearer {TOKEN}"})
print(r.status_code, r.text)
```

**cURL (create question)**

```bash
curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"How to setup FastAPI + Supabase?","body":"…","tags":["fastapi","supabase"],"visibility":"public"}' \
  http://localhost:8000/api/qa/questions
```

**cURL (rate + view)**

```bash
curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"entity":"rfh","entity_id":"<UUID>","stars":5}' \
  http://localhost:8000/api/ratings

curl -H "Content-Type: application/json" \
  -d '{"entity":"rfh","entity_id":"<UUID>"}' \
  http://localhost:8000/api/metrics/view
```

---

## 13) Troubleshooting

* **OAuth “Unable to exchange external code”**
  Ensure provider callback = **Supabase** callback:
  `https://<PROJECT-REF>.supabase.co/auth/v1/callback`
  And Supabase site URL matches your dev URL; SPA uses PKCE; deep link handler active.

* **401 Unauthorized on POSTs**
  Confirm Flutter sends `Authorization: Bearer <access_token>` (Supabase session). Re-check backend JWKS URL (must be `/auth/v1/keys`), clock skew, and CORS.

* **DB SSL errors (Windows)**
  Set `DB_SSL_MODE=relax` for local dev. In production use `require` or `verify-full`.

* **SQL `unnest(:tags::text[])` syntax error**
  With asyncpg bound params, **don’t** inline casts that way. Use:

  ```sql
  select unnest(:tags::text[])   -- OK with named bind param cast
  ```

  or

  ```sql
  select t from unnest(:tags) as t  -- pass a Python list, no explicit cast needed
  ```

* **go\_router assertion `uri.path.startsWith(newMatchedLocation)`**
  Caused by redirect loop/mismatch. Ensure initial routes & signin redirect logic don’t conflict; set `errorBuilder` fallback.

---

## 14) Directory Layout

```
backend/
  app/
    main.py
    core/config.py
    middleware/auth.py
    db/session.py
    utils/logger.py
    utils/dbhelpers.py
    api/
      deps.py
      v1/
        __init__.py
        routes_health.py
        routes_auth.py          (optional)
        routes_profiles.py
        routes_rfh.py
        routes_match.py
        routes_content.py
        routes_qa.py
        routes_projects.py
        routes_events.py
        routes_ratings.py
        routes_metrics.py
        routes_notifications.py (optional)
        routes_reports.py       (optional)
  .env
  requirements.txt

flutter/
  lib/
    main.dart
    config.dart
    routes.dart
    theme.dart
    services/api_client.dart
    widgets/common.dart
    screens/
      auth/
      home/
      rfh/
      qa/
      content/
      projects/
      events/
      profile/
      notifications/
```

---

## 15) Security Notes

* Validate JWT signature & issuer (Supabase domain) via JWKS.
* Keep RLS enabled (already in migration).
* Sanitize/limit uploads (size/type); consider signed URLs later.
* Rate limit sensitive endpoints (accept/reports) as usage grows.
* Log only necessary info; avoid storing tokens.

---

## 16) What We Have vs What We Want

**We have (MVP)**

* Auth: GitHub/Google via Supabase → token → backend protected endpoints.
* DB: rich schema with RLS, tags, ratings, views, feed view.
* API: profiles, RFH (CRUD owner), matching, content, Q\&A (delete/accept), projects, events, ratings/views.
* Flutter: sign-in, routable shells, lists/create/detail, rating + viewing, cleaner UI structure.

**We want (next)**

* File uploads (avatars + attachments) with UI pickers, thumbnails.
* Unified **feed** with helpfulness score + filters.
* Rich profiles (username display everywhere, verified badges).
* Powerful search (trgm + tsvector), filters, pagination, caching.
* Moderation + reports + admin pages.
* Agent assistant for triage, summarization, and matching suggestions.
* WebRTC/DM (or link-out) to enable guided help sessions.

