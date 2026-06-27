-- ML Revision — Supabase schema for cross-device progress sync.
--
-- How to run:
--   Supabase dashboard > SQL Editor > New query > paste this > Run.
--
-- Stores one row per user holding their whole progress object as JSON.
-- Row-Level Security ensures each user can only read/write their own row,
-- which is why the public "anon" key is safe to ship in the web app.

create table if not exists public.user_progress (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  progress   jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.user_progress enable row level security;

drop policy if exists "Users manage their own progress" on public.user_progress;
create policy "Users manage their own progress"
  on public.user_progress
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
