-- ============================================================
--  Platform DB Scaffold (Supabase / Postgres)
--  Run as a single migration in Supabase SQL Editor
-- ============================================================

-- Extensions
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";
create extension if not exists "pg_trgm";
create extension if not exists "unaccent";

-- ---------- Helper: timestamps ----------
create or replace function public.set_timestamp()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end$$;

-- ---------- Enums ----------
do $$
begin
  if not exists (select 1 from pg_type where typname = 'content_type') then
    create type content_type as enum (
      'best_practice','story','case_study','guide','course','webinar','workshop','video','material','news'
    );
  end if;

  if not exists (select 1 from pg_type where typname = 'evidence_level') then
    create type evidence_level as enum ('experience','observational','study','meta_analysis','n_a');
  end if;

  if not exists (select 1 from pg_type where typname = 'visibility') then
    create type visibility as enum ('public','members','private');
  end if;

  if not exists (select 1 from pg_type where typname = 'rfh_status') then
    create type rfh_status as enum ('open','matched','resolved','closed');
  end if;

  if not exists (select 1 from pg_type where typname = 'sensitivity') then
    create type sensitivity as enum ('normal','sensitive');
  end if;

  if not exists (select 1 from pg_type where typname = 'entity_kind') then
    create type entity_kind as enum ('content','question','answer','project','rfh','event','discussion_topic','forum_post');
  end if;

  if not exists (select 1 from pg_type where typname = 'role_kind') then
    create type role_kind as enum ('user','editor','moderator','admin','mentor','mentee','investor','founder');
  end if;
end$$;

-- ---------- Profiles (linked to auth.users) ----------
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique,
  full_name text,
  avatar_url text,
  bio text,
  languages text[] default array[]::text[],
  timezone text default 'America/Los_Angeles',
  country text,
  region text,
  roles role_kind[] default array['user']::role_kind[],
  reputation int default 0,
  offers text[] default array[]::text[], -- tags user can offer
  needs  text[] default array[]::text[], -- tags user needs
  anon_allowed boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create trigger trg_profiles_updated
before update on public.profiles
for each row execute procedure public.set_timestamp();

-- Auto-create profile on new user
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, username, full_name, avatar_url)
  values (new.id, split_part(new.email, '@', 1), coalesce(new.raw_user_meta_data->>'name',''), new.raw_user_meta_data->>'avatar_url')
  on conflict do nothing;
  return new;
end$$;

drop trigger if exists trg_on_auth_user_created on auth.users;
create trigger trg_on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

-- ---------- Tags ----------
create table if not exists public.tags (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  label text not null,
  created_at timestamptz default now()
);

-- ---------- Content (Best Practices, Guides, Stories, Materials, etc.) ----------
create table if not exists public.content (
  id uuid primary key default gen_random_uuid(),
  author_id uuid not null references public.profiles(id) on delete cascade,
  type content_type not null,
  title text not null,
  summary text,
  body text,
  evidence evidence_level default 'n_a',
  visibility visibility default 'public',
  sources jsonb default '[]',
  region text, -- local/ulusal içerikler için
  language text default 'tr',
  version int default 1,
  is_published boolean default true,
  tsv tsvector,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_content_author on public.content(author_id);
create index if not exists idx_content_tsv on public.content using gin(tsv);
create index if not exists idx_content_trgm on public.content using gin (title gin_trgm_ops);

create or replace function public.content_tsv_update()
returns trigger language plpgsql as $$
begin
  new.tsv :=
    setweight(to_tsvector('simple', unaccent(coalesce(new.title,''))), 'A') ||
    setweight(to_tsvector('simple', unaccent(coalesce(new.summary,''))), 'B') ||
    setweight(to_tsvector('simple', unaccent(coalesce(new.body,''))), 'C');
  return new;
end$$;

drop trigger if exists trg_content_tsv on public.content;
create trigger trg_content_tsv
before insert or update on public.content
for each row execute procedure public.content_tsv_update();

create trigger trg_content_updated
before update on public.content
for each row execute procedure public.set_timestamp();

-- Content ↔ Tags
create table if not exists public.content_tags (
  content_id uuid references public.content(id) on delete cascade,
  tag_id uuid references public.tags(id) on delete cascade,
  primary key (content_id, tag_id)
);

-- ---------- Q&A ----------
create table if not exists public.questions (
  id uuid primary key default gen_random_uuid(),
  asker_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  body text,
  tags text[] default array[]::text[],
  visibility visibility default 'public',
  accepted_answer_id uuid,
  tsv tsvector,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_questions_tsv on public.questions using gin(tsv);
create or replace function public.questions_tsv_update()
returns trigger language plpgsql as $$
begin
  new.tsv := setweight(to_tsvector('simple', unaccent(coalesce(new.title,''))), 'A')
           || setweight(to_tsvector('simple', unaccent(coalesce(new.body,''))), 'B');
  return new;
end$$;
drop trigger if exists trg_questions_tsv on public.questions;
create trigger trg_questions_tsv
before insert or update on public.questions
for each row execute procedure public.questions_tsv_update();

create trigger trg_questions_updated
before update on public.questions
for each row execute procedure public.set_timestamp();

create table if not exists public.answers (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references public.questions(id) on delete cascade,
  author_id uuid not null references public.profiles(id) on delete cascade,
  body text not null,
  evidence evidence_level default 'n_a',
  sources jsonb default '[]',
  is_accepted boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_answers_q on public.answers(question_id);
create trigger trg_answers_updated
before update on public.answers
for each row execute procedure public.set_timestamp();

-- link accepted answer
create or replace function public.accept_answer(p_question uuid, p_answer uuid, p_actor uuid)
returns void language plpgsql as $$
declare q_owner uuid;
begin
  select asker_id into q_owner from public.questions where id = p_question;
  if q_owner is null then
    raise exception 'Question not found';
  end if;
  if q_owner <> p_actor then
    raise exception 'Only question owner can accept an answer';
  end if;
  update public.answers set is_accepted = (id = p_answer) where question_id = p_question;
  update public.questions set accepted_answer_id = p_answer, updated_at = now() where id = p_question;
end$$;

-- ---------- RFH (Request for Help) & Matching ----------
create table if not exists public.rfh (
  id uuid primary key default gen_random_uuid(),
  requester_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  body text,
  tags text[] default array[]::text[],
  sensitivity sensitivity default 'normal',
  anonymous boolean default false,
  status rfh_status default 'open',
  region text,
  language text default 'tr',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create trigger trg_rfh_updated
before update on public.rfh
for each row execute procedure public.set_timestamp();

create table if not exists public.rfh_matches (
  rfh_id uuid references public.rfh(id) on delete cascade,
  helper_id uuid references public.profiles(id) on delete cascade,
  score numeric default 0,
  note text,
  created_at timestamptz default now(),
  primary key (rfh_id, helper_id)
);

-- Masked public view for anonymous RFH
create or replace view public.rfh_public as
select
  id,
  case when anonymous and requester_id <> auth.uid()
       and not (exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)))
       then null else requester_id end as requester_id,
  title, body, tags, sensitivity, anonymous, status, region, language,
  created_at, updated_at
from public.rfh;

-- ---------- Mentorship ----------
create table if not exists public.mentorship (
  id uuid primary key default gen_random_uuid(),
  mentor_id uuid not null references public.profiles(id) on delete cascade,
  mentee_id uuid not null references public.profiles(id) on delete cascade,
  topics text[] default array[]::text[],
  status text default 'pending', -- pending/active/ended
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (mentor_id, mentee_id)
);
create trigger trg_mentorship_updated
before update on public.mentorship
for each row execute procedure public.set_timestamp();

-- ---------- Projects & Teams ----------
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  description text,
  needed_roles text[] default array[]::text[],
  region text,
  tags text[] default array[]::text[],
  visibility visibility default 'public',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create trigger trg_projects_updated
before update on public.projects
for each row execute procedure public.set_timestamp();

create table if not exists public.project_members (
  project_id uuid references public.projects(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade,
  role text default 'member',
  joined_at timestamptz default now(),
  primary key (project_id, user_id)
);

create table if not exists public.project_applications (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  applicant_id uuid references public.profiles(id) on delete cascade,
  message text,
  status text default 'pending', -- pending/accepted/rejected
  created_at timestamptz default now()
);

-- ---------- Events (courses/webinars/workshops) ----------
create table if not exists public.events (
  id uuid primary key default gen_random_uuid(),
  host_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  description text,
  type content_type not null check (type in ('course','webinar','workshop')),
  starts_at timestamptz not null,
  ends_at timestamptz,
  location text, -- url or venue
  capacity int,
  tags text[] default array[]::text[],
  visibility visibility default 'public',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create trigger trg_events_updated
before update on public.events
for each row execute procedure public.set_timestamp();

create table if not exists public.event_enrollments (
  event_id uuid references public.events(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade,
  status text default 'going', -- going/waitlist/cancelled
  created_at timestamptz default now(),
  primary key (event_id, user_id)
);

-- ---------- Discussions / Forums ----------
create table if not exists public.discussion_topics (
  id uuid primary key default gen_random_uuid(),
  creator_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  body text,
  tags text[] default array[]::text[],
  visibility visibility default 'public',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create trigger trg_disc_topics_updated
before update on public.discussion_topics
for each row execute procedure public.set_timestamp();

create table if not exists public.forum_posts (
  id uuid primary key default gen_random_uuid(),
  topic_id uuid not null references public.discussion_topics(id) on delete cascade,
  author_id uuid not null references public.profiles(id) on delete cascade,
  body text not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create trigger trg_forum_posts_updated
before update on public.forum_posts
for each row execute procedure public.set_timestamp();

-- ---------- Comments (unified, polymorphic via entity_kind) ----------
create table if not exists public.comments (
  id uuid primary key default gen_random_uuid(),
  entity entity_kind not null,
  entity_id uuid not null,
  author_id uuid not null references public.profiles(id) on delete cascade,
  body text not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_comments_entity on public.comments(entity, entity_id);
create trigger trg_comments_updated
before update on public.comments
for each row execute procedure public.set_timestamp();

-- ---------- Notifications ----------
create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  type text not null,
  payload jsonb not null,
  read_at timestamptz,
  created_at timestamptz default now()
);
create index if not exists idx_notifications_user on public.notifications(user_id, read_at);

-- ---------- Moderation / Reports ----------
create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  reporter_id uuid references public.profiles(id) on delete set null,
  entity entity_kind not null,
  entity_id uuid not null,
  reason text,
  severity int default 1,
  state text default 'open', -- open/under_review/closed
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create trigger trg_reports_updated
before update on public.reports
for each row execute procedure public.set_timestamp();

-- ---------- Reputation / Badges ----------
create table if not exists public.badges (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  name text not null,
  description text,
  created_at timestamptz default now()
);

create table if not exists public.user_badges (
  user_id uuid references public.profiles(id) on delete cascade,
  badge_id uuid references public.badges(id) on delete cascade,
  granted_by uuid references public.profiles(id) on delete set null,
  granted_at timestamptz default now(),
  primary key (user_id, badge_id)
);

create or replace function public.add_reputation(p_user uuid, delta int)
returns void language sql as $$
  update public.profiles set reputation = greatest(0, reputation + delta), updated_at = now()
  where id = p_user;
$$;

-- ---------- Search View (unified) ----------
create or replace view public.feed_union as
select id, 'content'::entity_kind as kind, title, summary, author_id as owner_id, tags.array_agg as tags, created_at, updated_at
from (
  select c.id, c.title, coalesce(c.summary, left(c.body, 240)) as summary, c.author_id, array_remove(array_agg(ctag.label), null) as array_agg, c.created_at, c.updated_at
  from public.content c
  left join public.content_tags ct on ct.content_id = c.id
  left join public.tags ctag on ctag.id = ct.tag_id
  where c.is_published = true and c.visibility = 'public'
  group by c.id
) s
union all
select q.id, 'question', q.title, left(coalesce(q.body,''),240), q.asker_id, q.tags, q.created_at, q.updated_at from public.questions q
union all
select p.id, 'project', p.title, left(coalesce(p.description,''),240), p.owner_id, p.tags, p.created_at, p.updated_at from public.projects p
union all
select r.id, 'rfh', r.title, left(coalesce(r.body,''),240),
       case when r.anonymous and r.requester_id <> auth.uid() then null else r.requester_id end,
       r.tags, r.created_at, r.updated_at
from public.rfh r;

-- ============================================================
-- RLS (Row Level Security) Policies
-- ============================================================

-- Enable RLS where needed
alter table public.profiles enable row level security;
alter table public.content enable row level security;
alter table public.content_tags enable row level security;
alter table public.tags enable row level security;
alter table public.questions enable row level security;
alter table public.answers enable row level security;
alter table public.rfh enable row level security;
alter table public.rfh_matches enable row level security;
alter table public.mentorship enable row level security;
alter table public.projects enable row level security;
alter table public.project_members enable row level security;
alter table public.project_applications enable row level security;
alter table public.events enable row level security;
alter table public.event_enrollments enable row level security;
alter table public.discussion_topics enable row level security;
alter table public.forum_posts enable row level security;
alter table public.comments enable row level security;
alter table public.notifications enable row level security;
alter table public.reports enable row level security;
alter table public.badges enable row level security;
alter table public.user_badges enable row level security;

-- Profiles
create policy "profiles_select_public" on public.profiles
for select using (true);

create policy "profiles_update_own" on public.profiles
for update using (auth.uid() = id)
with check (auth.uid() = id);

-- Tags
create policy "tags_read_all" on public.tags
for select using (true);
create policy "tags_write_admin" on public.tags
for insert with check (exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)));
create policy "tags_update_admin" on public.tags
for update using (exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)));

-- Content
create policy "content_read_public_or_owner" on public.content
for select using (
  visibility = 'public'
  or author_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles))
);
create policy "content_insert_self" on public.content
for insert with check (author_id = auth.uid());
create policy "content_update_owner" on public.content
for update using (author_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)))
with check (author_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)));

-- Content Tags (author or admin)
create policy "content_tags_manage_by_author" on public.content_tags
for all using (
  exists (select 1 from public.content c where c.id = content_id and (c.author_id = auth.uid()
    or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)))))
with check (
  exists (select 1 from public.content c where c.id = content_id and (c.author_id = auth.uid()
    or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)))));

-- Questions & Answers
create policy "questions_read" on public.questions
for select using (visibility = 'public' or asker_id = auth.uid());
create policy "questions_insert" on public.questions
for insert with check (asker_id = auth.uid());
create policy "questions_update_owner" on public.questions
for update using (asker_id = auth.uid())
with check (asker_id = auth.uid());

create policy "answers_read" on public.answers
for select using (true);
create policy "answers_insert" on public.answers
for insert with check (author_id = auth.uid());
create policy "answers_update_owner" on public.answers
for update using (author_id = auth.uid())
with check (author_id = auth.uid());

-- RFH
create policy "rfh_select_masked" on public.rfh
for select using (true);
create policy "rfh_insert_self" on public.rfh
for insert with check (requester_id = auth.uid());
create policy "rfh_update_owner" on public.rfh
for update using (requester_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)))
with check (requester_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)));

create policy "rfh_matches_read_all" on public.rfh_matches
for select using (true);
create policy "rfh_matches_upsert_admin_or_helper" on public.rfh_matches
for all using (helper_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)))
with check (helper_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)));

-- Mentorship
create policy "mentorship_read_owner" on public.mentorship
for select using (mentor_id = auth.uid() or mentee_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)));
create policy "mentorship_insert_self" on public.mentorship
for insert with check (mentor_id = auth.uid() or mentee_id = auth.uid());
create policy "mentorship_update_parties" on public.mentorship
for update using (mentor_id = auth.uid() or mentee_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)))
with check (mentor_id = auth.uid() or mentee_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)));

-- Projects
create policy "projects_read_public_or_member" on public.projects
for select using (visibility = 'public' or owner_id = auth.uid()
  or exists (select 1 from public.project_members pm where pm.project_id = id and pm.user_id = auth.uid()));
create policy "projects_insert_owner" on public.projects
for insert with check (owner_id = auth.uid());
create policy "projects_update_owner" on public.projects
for update using (owner_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)))
with check (owner_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)));

create policy "project_members_manage_owner" on public.project_members
for all using (
  exists (select 1 from public.projects pr where pr.id = project_id and pr.owner_id = auth.uid())
  or user_id = auth.uid()
) with check (
  exists (select 1 from public.projects pr where pr.id = project_id and pr.owner_id = auth.uid())
  or user_id = auth.uid()
);

create policy "project_apps_read_owner_or_self" on public.project_applications
for select using (
  applicant_id = auth.uid()
  or exists (select 1 from public.projects pr where pr.id = project_id and pr.owner_id = auth.uid())
);
create policy "project_apps_insert_self" on public.project_applications
for insert with check (applicant_id = auth.uid());
create policy "project_apps_update_owner" on public.project_applications
for update using (
  applicant_id = auth.uid()
  or exists (select 1 from public.projects pr where pr.id = project_id and pr.owner_id = auth.uid())
) with check (
  applicant_id = auth.uid()
  or exists (select 1 from public.projects pr where pr.id = project_id and pr.owner_id = auth.uid())
);

-- Events
create policy "events_read_public_or_host" on public.events
for select using (visibility = 'public' or host_id = auth.uid());
create policy "events_insert_host" on public.events
for insert with check (host_id = auth.uid());
create policy "events_update_host" on public.events
for update using (host_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)))
with check (host_id = auth.uid()
  or exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)));

create policy "event_enroll_self" on public.event_enrollments
for all using (user_id = auth.uid()
  or exists (select 1 from public.events e where e.id = event_id and e.host_id = auth.uid()))
with check (user_id = auth.uid()
  or exists (select 1 from public.events e where e.id = event_id and e.host_id = auth.uid()));

-- Discussions
create policy "topics_read_public_or_creator" on public.discussion_topics
for select using (visibility = 'public' or creator_id = auth.uid());
create policy "topics_insert_self" on public.discussion_topics
for insert with check (creator_id = auth.uid());
create policy "topics_update_creator" on public.discussion_topics
for update using (creator_id = auth.uid())
with check (creator_id = auth.uid());

create policy "posts_read_all" on public.forum_posts
for select using (true);
create policy "posts_insert_self" on public.forum_posts
for insert with check (author_id = auth.uid());
create policy "posts_update_self" on public.forum_posts
for update using (author_id = auth.uid())
with check (author_id = auth.uid());

-- Comments
create policy "comments_read_all" on public.comments
for select using (true);
create policy "comments_insert_self" on public.comments
for insert with check (author_id = auth.uid());
create policy "comments_update_self" on public.comments
for update using (author_id = auth.uid())
with check (author_id = auth.uid());

-- Notifications (user-only)
create policy "notifications_read_self" on public.notifications
for select using (user_id = auth.uid());
create policy "notifications_write_self" on public.notifications
for all using (user_id = auth.uid())
with check (user_id = auth.uid());

-- Reports
create policy "reports_read_mods" on public.reports
for select using (exists (select 1 from public.profiles p where p.id = auth.uid() and ( 'moderator' = any(p.roles) or 'admin' = any(p.roles))));
create policy "reports_insert_auth" on public.reports
for insert with check (auth.uid() is not null);
create policy "reports_update_mods" on public.reports
for update using (exists (select 1 from public.profiles p where p.id = auth.uid() and ( 'moderator' = any(p.roles) or 'admin' = any(p.roles))))
with check (exists (select 1 from public.profiles p where p.id = auth.uid() and ( 'moderator' = any(p.roles) or 'admin' = any(p.roles))));

-- Badges
create policy "badges_read_all" on public.badges
for select using (true);
create policy "user_badges_read_self_or_public" on public.user_badges
for select using (user_id = auth.uid() or exists (select 1 from public.profiles p where p.id = user_id));
create policy "user_badges_grant_admin" on public.user_badges
for insert with check (exists (select 1 from public.profiles p where p.id = auth.uid() and 'admin' = any(p.roles)));

-- ============================================================
-- Seed minimal tags / badges (optional)
-- ============================================================
insert into public.tags (slug, label) values
  ('addiction-recovery','Addiction Recovery'),
  ('leadership','Leadership'),
  ('software-testing','Software Testing'),
  ('flutter','Flutter'),
  ('fastapi','FastAPI'),
  ('ai-ml','AI/ML'),
  ('career','Career'),
  ('fundraising','Fundraising')
on conflict do nothing;

insert into public.badges (slug, name, description) values
  ('mentor-verified','Verified Mentor','Kapsam ve etik onayı geçmiş mentorluk profili'),
  ('editor','Editor','Best practice içeriklerini gözden geçiren editör'),
  ('impact-30','Impact 30','30+ çözülmüş yardım talebi (RFH)'),
  ('knowledge-sharer','Knowledge Sharer','Kaynaklı, kanıt düzeyli katkılar')
on conflict do nothing;
