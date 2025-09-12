# Benefisocial
İnsanların en hayırlısı insanlara faydalı olandır 


⸻

BenefiSocial — MVP (FastAPI + Supabase + Flutter)

Purpose: A purpose-driven social platform where people share best practices, ask for help (RFH), form teams, learn, and collaborate — with OAuth login (GitHub/Google) via Supabase, a FastAPI backend, and a Flutter multi-platform UI.

Monorepo layout:

/backend      # FastAPI app (Part 1 + Part 2 scaffolds)
/frontend     # Flutter app (UI Part 1 + Part 2 scaffolds)


⸻

1) Prerequisites
	•	Supabase account + project
	•	Python 3.11+
	•	Node/Flutter not required for backend; Flutter SDK 3.22+ for frontend
	•	Docker (optional)

⸻

2) Supabase Setup (Auth + Keys)
	1.	Create a Supabase project.
	2.	Enable OAuth providers you want (e.g., GitHub, Google)
Console → Authentication → Providers → enable & configure redirect URLs (e.g., http://localhost:3000, http://localhost:5173, and your Flutter web origin; for mobile, you can use deep links later).
	3.	Collect:
	•	Project URL (e.g., https://YOUR_PROJECT.supabase.co)
	•	Anon/Public Key (for the Flutter app)
	•	JWKS URL for the backend:
https://YOUR_PROJECT.supabase.co/auth/v1/.well-known/jwks.json
	•	Audience is typically "authenticated".

In dev, allow http://127.0.0.1:8000 (backend) and your Flutter web origin in Auth → URL Configuration and CORS (see below).

⸻

3) Database Schema (run in Supabase SQL Editor)

Paste and run this once:

-- Extensions (usually already present in Supabase)
create extension if not exists pgcrypto;
create extension if not exists "uuid-ossp";

-- USERS / PROFILES
create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(), -- match Supabase auth.users.id where possible
  username text unique,
  full_name text,
  avatar_url text,
  bio text,
  languages text[],
  timezone text,
  country text,
  region text,
  roles text[],
  reputation int default 0,
  offers text[], -- tags of help they can offer
  needs text[],
  anon_allowed boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- REQUESTS FOR HELP (RFH)
create table if not exists public.rfh (
  id uuid primary key default gen_random_uuid(),
  requester_id uuid references public.profiles(id) on delete set null,
  title text not null,
  body text,
  tags text[] default '{}',
  sensitivity text default 'normal',
  anonymous boolean default false,
  status text default 'open', -- open|in_progress|resolved|hidden
  region text,
  language text default 'tr',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- A public view (used by list endpoints)
create or replace view public.rfh_public as
select
  id, requester_id, title, body, tags, sensitivity, anonymous, status, region, language,
  created_at, updated_at
from public.rfh
where status in ('open','in_progress','resolved');

-- CONTENT + TAGS
create table if not exists public.content (
  id uuid primary key default gen_random_uuid(),
  author_id uuid references public.profiles(id) on delete set null,
  type text not null, -- best_practice|guide|story|case_study|video|...
  title text not null,
  summary text,
  body text,
  evidence text default 'n_a',
  visibility text default 'public', -- public|unlisted|private
  sources jsonb default '[]'::jsonb,
  region text,
  language text default 'tr',
  is_published boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.tags (
  id bigserial primary key,
  slug text unique not null,
  label text
);

create table if not exists public.content_tags (
  content_id uuid references public.content(id) on delete cascade,
  tag_id bigint references public.tags(id) on delete cascade,
  primary key (content_id, tag_id)
);

-- Q&A
create table if not exists public.questions (
  id uuid primary key default gen_random_uuid(),
  asker_id uuid references public.profiles(id) on delete set null,
  title text not null,
  body text,
  tags text[] default '{}',
  visibility text default 'public',
  created_at timestamptz default now()
);

create table if not exists public.answers (
  id uuid primary key default gen_random_uuid(),
  question_id uuid references public.questions(id) on delete cascade,
  author_id uuid references public.profiles(id) on delete set null,
  body text not null,
  evidence text default 'n_a',
  sources jsonb default '[]'::jsonb,
  is_accepted boolean default false,
  created_at timestamptz default now()
);

-- PROJECTS
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references public.profiles(id) on delete set null,
  title text not null,
  description text,
  needed_roles text[] default '{}',
  region text,
  tags text[] default '{}',
  visibility text default 'public',
  created_at timestamptz default now()
);

create table if not exists public.project_members (
  project_id uuid references public.projects(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade,
  role text default 'member',
  primary key (project_id, user_id)
);

create table if not exists public.project_applications (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  applicant_id uuid references public.profiles(id) on delete cascade,
  message text,
  status text default 'pending',
  created_at timestamptz default now()
);

-- EVENTS
create table if not exists public.events (
  id uuid primary key default gen_random_uuid(),
  host_id uuid references public.profiles(id) on delete set null,
  title text not null,
  description text,
  type text not null, -- course|webinar|workshop
  starts_at timestamptz not null,
  ends_at timestamptz,
  location text,
  capacity int,
  tags text[] default '{}',
  visibility text default 'public',
  created_at timestamptz default now()
);

create table if not exists public.event_enrollments (
  event_id uuid references public.events(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade,
  status text default 'going',
  primary key (event_id, user_id),
  created_at timestamptz default now()
);

-- NOTIFICATIONS
create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade,
  type text not null,
  payload jsonb default '{}'::jsonb,
  read_at timestamptz,
  created_at timestamptz default now()
);

-- REPORTS
create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  reporter_id uuid references public.profiles(id) on delete set null,
  entity text not null,
  entity_id text not null,
  reason text,
  severity int default 1,
  created_at timestamptz default now()
);

-- Useful indexes
create index if not exists idx_rfh_tags on public.rfh using gin (tags);
create index if not exists idx_profiles_offers on public.profiles using gin (offers);
create index if not exists idx_content_is_published on public.content (is_published);
create index if not exists idx_questions_tags on public.questions using gin (tags);


⸻

4) Backend (FastAPI)

If you used the provided generator scripts:
	•	Part 1: generate_scaffold_part1.py
	•	Part 2: generate_scaffold_part2.py

Setup

cd backend
python -m venv .venv
source .venv/bin/activate                      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

Edit .env:

DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require
SUPABASE_JWKS_URL=https://YOUR_PROJECT.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_AUDIENCE=authenticated
DEV_ALLOW_UNVERIFIED=true   # dev only; allows anon GETs
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:5173,http://localhost:8080

Run:

./uvicorn_dev.sh
# or: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

API Docs: http://127.0.0.1:8000/api/docs

Docker (optional):

cd backend
docker compose -f docker/docker-compose.yml up --build


⸻

5) Flutter Frontend

If you used the UI scaffold scripts:
	•	Part 1: ui_scaffold1.py (Auth, RFH, Profile)
	•	Part 2: ui_scaffold2.py (Content, Q&A, Projects, Events, Notifications)

Setup

cd frontend
bash create_flutter_app.sh   # runs `flutter create .` if needed
flutter pub get

Edit lib/config.dart:

const SUPABASE_URL = "https://YOUR_PROJECT.supabase.co";
const SUPABASE_ANON_KEY = "YOUR_SUPABASE_ANON_KEY";
const BACKEND_BASE_URL = "http://127.0.0.1:8000";
const API_PREFIX = "/api";

Run:

flutter run -d chrome
# or: flutter run -d macos / linux / windows / android

Sign in with GitHub or Google → you’ll see tabs, create content/RFH/etc.
The app sends the Supabase JWT to backend with Authorization: Bearer <token>.

⸻

6) Endpoint Map (MVP)
	•	Health: GET /api/healthz
	•	Auth: GET /api/auth/me
	•	Profiles:
	•	GET /api/profiles/me
	•	PUT /api/profiles/me
	•	RFH (Request for Help):
	•	POST /api/rfh
	•	GET /api/rfh (search by q, tag)
	•	GET /api/rfh/{id}
	•	GET /api/match/{rfh_id}
	•	Content:
	•	POST /api/content
	•	GET /api/content (search q, tag)
	•	Q&A:
	•	POST /api/qa/questions
	•	GET /api/qa/questions
	•	POST /api/qa/answers
	•	GET /api/qa/questions/{id}/answers
	•	Projects:
	•	POST /api/projects
	•	GET /api/projects
	•	POST /api/projects/{id}/apply
	•	Events:
	•	POST /api/events
	•	GET /api/events
	•	POST /api/events/{id}/enroll
	•	Notifications:
	•	GET /api/notifications
	•	Reports:
	•	POST /api/reports

⸻

7) Quick Smoke Test (curl)

# health
curl http://127.0.0.1:8000/api/healthz

# with token (replace $TOKEN with Supabase access_token)
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/profiles/me

# create RFH
curl -X POST http://127.0.0.1:8000/api/rfh \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Need a Flutter mentor","body":"Pair for 2h","tags":["flutter","mentoring"],"anonymous":false}'


⸻

8) Common Pitfalls & Fixes
	•	401/Token error: Verify SUPABASE_JWKS_URL and SUPABASE_AUDIENCE. Ensure the client is truly logged in and passing the access_token.
	•	CORS error: Add your Flutter/Web origins to backend CORS_ORIGINS and Supabase Auth Allowed Redirect URLs.
	•	DB SSL: Use ?sslmode=require in DATABASE_URL for Supabase.
	•	Profiles missing: You may need to seed a profile that matches auth.users.id. Quick fix during dev: insert a profile row with the Supabase user UUID after your first login.
	•	DEV_ALLOW_UNVERIFIED: Keep true only for dev; switch to false in staging/prod.

⸻

9) Roadmap Notes
	•	Add TimeCoin, AdilOS, AdilNet integrations (ledger, decentralized identity/storage).
	•	Real-time streams (notifications, chat) via Supabase Realtime.
	•	File uploads (Supabase Storage) for avatars & content.
	•	Moderation pipeline + reputation scoring.

⸻

10) License

MIT (or your preferred license).

⸻

BenefiSocial — MVP (FastAPI + Supabase + Flutter) — Türkçe

Amaç: İnsanların iyi uygulamaları paylaştığı, yardım istediği (RFH), ekip kurduğu, öğrendiği ve iş birliği yaptığı bir platform. Giriş Supabase OAuth (GitHub/Google) ile; backend FastAPI; arayüz Flutter.

Monorepo:

/backend   # FastAPI uygulaması
/frontend  # Flutter uygulaması


⸻

1) Ön Koşullar
	•	Supabase hesabı + proje
	•	Python 3.11+
	•	Flutter SDK 3.22+ (UI için)
	•	Docker (opsiyonel)

⸻

2) Supabase Kurulumu (Auth + Anahtarlar)
	1.	Supabase projesi oluşturun.
	2.	OAuth sağlayıcılarını açın (örn. GitHub, Google)
Konsol → Authentication → Providers → Redirect URL’lere yerelde kullandığınız web origin’lerini ekleyin (örn. http://localhost:3000, http://127.0.0.1:5173, Flutter web origin).
	3.	Şunları alın:
	•	Project URL (örn. https://YOUR_PROJECT.supabase.co)
	•	Anon/Public Key (Flutter için)
	•	JWKS URL (backend için):
https://YOUR_PROJECT.supabase.co/auth/v1/.well-known/jwks.json
	•	Audience genellikle "authenticated".

⸻

3) Veritabanı Şeması (Supabase SQL Editor’da çalıştırın)

Yukarıdaki SQL bloğunu birebir kopyalayıp çalıştırın. Tablolar/indeksler ve rfh_public görünümü oluşturulur.

⸻

4) Backend (FastAPI)

Eğer generator’ları kullandıysanız:
	•	Part 1: generate_scaffold_part1.py
	•	Part 2: generate_scaffold_part2.py

Kurulum

cd backend
python -m venv .venv
source .venv/bin/activate                      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

.env düzenleyin:

DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require
SUPABASE_JWKS_URL=https://YOUR_PROJECT.supabase.co/auth/v1/.well
