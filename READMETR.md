⸻

BenefiSocial — MVP (FastAPI + Supabase + Flutter) — Türkçe

Amaç: İnsanların iyi uygulamaları paylaştığı, yardım istediği (RFH – request for help), ekip kurduğu, öğrendiği ve dayanıştığı bir sosyal platform. Giriş Supabase OAuth (GitHub/Google) ile; backend FastAPI; arayüz Flutter.

Monorepo yapısı:

/backend   # FastAPI uygulaması (Scaffold Part 1 + Part 2)
/frontend  # Flutter uygulaması (UI Scaffold Part 1 + Part 2)


⸻

1) Ön Koşullar
	•	Supabase hesabı + proje
	•	Python 3.11+
	•	Flutter SDK 3.22+ (UI için)
	•	Docker (opsiyonel)
	•	Yerelde test için: http://127.0.0.1:8000 (backend), http://localhost/http://127.0.0.1 (Flutter web)

⸻

2) Hızlı Başlangıç (Özet)

# 1) Supabase’te proje aç, OAuth (GitHub/Google) etkinleştir, URL/KEY’leri not al
# 2) DB şemasını Supabase SQL Editor’a yapıştır (aşağıdaki SQL)
# 3) Backend’i çalıştır
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # değişkenleri doldurun
./uvicorn_dev.sh

# 4) Frontend’i çalıştır
cd ../frontend
bash create_flutter_app.sh
flutter pub get
# lib/config.dart içini doldurun (Supabase URL/Anon Key + Backend URL)
flutter run -d chrome

# 5) Web’de GitHub/Google ile giriş yapın ve sekmeleri gezin


⸻

3) Supabase Kurulumu (Auth + Anahtarlar)
	1.	Supabase projesi oluşturun.
	2.	Authentication → Providers bölümünden GitHub ve/veya Google sağlayıcılarını etkinleştirin.
	•	Redirect URL’lere yerel origin’leri ekleyin (ör. Flutter web için http://localhost:xxxxx veya http://127.0.0.1:xxxxx).
	3.	Şu değerleri not alın:
	•	Project URL: https://YOUR_PROJECT.supabase.co
	•	Anon/Public Key: (Flutter’da kullanılacak)
	•	JWKS URL (backend için):
https://YOUR_PROJECT.supabase.co/auth/v1/.well-known/jwks.json
	•	Audience: Genellikle "authenticated"
	4.	Supabase Auth → URL Configuration ve backend CORS için kullandığınız web origin’lerini eklemeyi unutmayın.

⸻

4) Veritabanı Şeması (Supabase SQL Editor’da çalıştırın)

Aşağıdaki SQL bloğunu bir kez çalıştırmanız yeterli:

-- Extensions (genelde hazır gelir)
create extension if not exists pgcrypto;
create extension if not exists "uuid-ossp";

-- USERS / PROFILES
create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
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
  offers text[],
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

-- Listeleme için public view
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

-- Indeksler
create index if not exists idx_rfh_tags on public.rfh using gin (tags);
create index if not exists idx_profiles_offers on public.profiles using gin (offers);
create index if not exists idx_content_is_published on public.content (is_published);
create index if not exists idx_questions_tags on public.questions using gin (tags);


⸻

5) Backend (FastAPI)

Scaffold’ları çalıştırdıysanız:
	•	Part 1: generate_scaffold_part1.py
	•	Part 2: generate_scaffold_part2.py

Kurulum

cd backend
python -m venv .venv
source .venv/bin/activate                    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

.env örneği:

DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require
SUPABASE_JWKS_URL=https://YOUR_PROJECT.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_AUDIENCE=authenticated
DEV_ALLOW_UNVERIFIED=true
LOG_LEVEL=info
API_PREFIX=/api
APP_NAME=NovaBridge
APP_ENV=dev
APP_HOST=0.0.0.0
APP_PORT=8000
REQUEST_TIMEOUT=15
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:5173,http://localhost:8080

Çalıştırma

./uvicorn_dev.sh
# veya:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

API Dokümanı: http://127.0.0.1:8000/api/docs

Docker (opsiyonel):

cd backend
docker compose -f docker/docker-compose.yml up --build


⸻

6) Flutter (Frontend)

UI scaffold’ları çalıştırdıysanız:
	•	Part 1: ui_scaffold1.py (Auth, RFH, Profile)
	•	Part 2: ui_scaffold2.py (Content, Q&A, Projects, Events, Notifications)

Kurulum

cd frontend
bash create_flutter_app.sh
flutter pub get

lib/config.dart düzenleyin:

const SUPABASE_URL = "https://YOUR_PROJECT.supabase.co";
const SUPABASE_ANON_KEY = "YOUR_SUPABASE_ANON_KEY";
const BACKEND_BASE_URL = "http://127.0.0.1:8000";
const API_PREFIX = "/api";

Çalıştırma

flutter run -d chrome
# (tercihen) flutter run -d macos / linux / windows / android

Giriş: GitHub/Google OAuth. Oturum açınca sekmeler aktif olur. Flutter, Supabase JWT’sini Authorization: Bearer <token> olarak backend’e iletir.

⸻

7) API Haritası (MVP)
	•	Health: GET /api/healthz
	•	Auth: GET /api/auth/me
	•	Profiles:
	•	GET /api/profiles/me
	•	PUT /api/profiles/me
	•	RFH (Request for Help):
	•	POST /api/rfh
	•	GET /api/rfh (q, tag ile arama)
	•	GET /api/rfh/{id}
	•	GET /api/match/{rfh_id}
	•	Content:
	•	POST /api/content
	•	GET /api/content (q, tag)
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

8) Hızlı Duman Testi (curl)

# Health
curl http://127.0.0.1:8000/api/healthz

# (TOKEN: Supabase access_token)
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/profiles/me

# RFH oluştur
curl -X POST http://127.0.0.1:8000/api/rfh \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Flutter mentoru arıyorum","body":"2 saat pair","tags":["flutter","mentoring"],"anonymous":false}'


⸻

9) Sorun Giderme (Sık Karşılaşılanlar)
	•	401 / Token hatası:
SUPABASE_JWKS_URL ve SUPABASE_AUDIENCE değerlerini kontrol edin. Flutter tarafında gerçekten giriş yapıldı mı? access_token gönderiliyor mu?
	•	CORS hatası:
Backend .env içindeki CORS_ORIGINS ve Supabase Auth Allowed Redirect URLs listesine kullandığınız origin’leri (ör. http://localhost:xxxxx) ekleyin.
	•	DB SSL:
Supabase için DATABASE_URL sonunda ?sslmode=require kullanın.
	•	Profil bulunamadı:
İlk girişten sonra auth.users.id ile eşleşen bir profil satırı olmayabilir. Geliştirmede hızlı çözüm: giriş yaptığınız kullanıcının UUID’si ile public.profiles tablosuna satır ekleyin.
	•	DEV_ALLOW_UNVERIFIED:
Sadece geliştirmede true tutun; canlıda false yapın.
	•	Tarayıcı OAuth redirect:
Supabase’deki redirect origin/URL’ler ile Flutter web’in çalıştığı port uyumlu olmalı.

⸻

10) Yol Haritası
	•	TimeCoin, AdilOS, AdilNet entegrasyonları (defter, kimlik, depolama).
	•	Supabase Realtime ile gerçek zamanlı bildirim/sohbet.
	•	Supabase Storage ile dosya yükleme (avatar, içerik).
	•	Moderasyon/raporlama akışı ve itibar (reputation) puanlaması.

⸻

11) Lisans

MIT (veya tercih ettiğiniz lisans).

⸻

güle güle kullanın! herhangi bir yerde takılırsanız, hatayı/çıktıyı bana bırakın — birlikte çözelim 💚
