-- Candidate Match (/quiz) — anonymous usage counts + officer race toggles.
-- Apply in the WTPPPA civic Supabase project (SQL editor → paste → Run).
-- No PII is stored: no IPs, no answers, no emails except admin logins.

-- ── Usage events ─────────────────────────────────────────────────────
create table if not exists public.quiz_events (
  id         bigserial primary key,
  created_at timestamptz not null default now(),
  event      text not null check (event in ('start', 'complete', 'reveal')),
  mode       text check (mode in ('short', 'long')),
  race_id    text check (char_length(race_id) <= 16),
  answered   int  check (answered between 0 and 50),
  source     text check (char_length(source) <= 40)  -- ?src= / utm_source, e.g. "email"
);
create index if not exists quiz_events_created_at on public.quiz_events (created_at);

-- ── Officer-controlled race visibility ───────────────────────────────
create table if not exists public.quiz_race_settings (
  race_id    text primary key check (char_length(race_id) <= 16),
  visible    boolean not null default true,
  updated_at timestamptz not null default now(),
  updated_by text
);

create table if not exists public.quiz_admins (
  email text primary key
);

create table if not exists public.quiz_admin_log (
  id      bigserial primary key,
  at      timestamptz not null default now(),
  email   text,
  race_id text,
  visible boolean
);

create or replace function public.is_quiz_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.quiz_admins where lower(email) = lower(auth.jwt() ->> 'email'));
$$;

-- Stamp + audit every visibility change.
create or replace function public.quiz_race_settings_audit() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.updated_at := now();
  new.updated_by := auth.jwt() ->> 'email';
  insert into public.quiz_admin_log (email, race_id, visible) values (new.updated_by, new.race_id, new.visible);
  return new;
end $$;

drop trigger if exists quiz_race_settings_audit on public.quiz_race_settings;
create trigger quiz_race_settings_audit before insert or update on public.quiz_race_settings
  for each row execute function public.quiz_race_settings_audit();

-- ── RLS ──────────────────────────────────────────────────────────────
alter table public.quiz_events        enable row level security;
alter table public.quiz_race_settings enable row level security;
alter table public.quiz_admins        enable row level security;
alter table public.quiz_admin_log     enable row level security;

drop policy if exists "anyone can log an event" on public.quiz_events;
create policy "anyone can log an event" on public.quiz_events
  for insert to anon, authenticated with check (true);

drop policy if exists "admins read events" on public.quiz_events;
create policy "admins read events" on public.quiz_events
  for select to authenticated using (public.is_quiz_admin());

drop policy if exists "anyone reads race settings" on public.quiz_race_settings;
create policy "anyone reads race settings" on public.quiz_race_settings
  for select to anon, authenticated using (true);

drop policy if exists "admins write race settings" on public.quiz_race_settings;
create policy "admins write race settings" on public.quiz_race_settings
  for all to authenticated using (public.is_quiz_admin()) with check (public.is_quiz_admin());

drop policy if exists "admins read admins" on public.quiz_admins;
create policy "admins read admins" on public.quiz_admins
  for select to authenticated using (public.is_quiz_admin());

drop policy if exists "admins read log" on public.quiz_admin_log;
create policy "admins read log" on public.quiz_admin_log
  for select to authenticated using (public.is_quiz_admin());

-- ── Aggregates for the admin page (Supabase caps raw selects at 1k rows) ──
create or replace function public.quiz_stats(since timestamptz default now() - interval '30 days')
returns json language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_quiz_admin() then
    raise exception 'not authorized';
  end if;
  return json_build_object(
    'totals',  (select coalesce(json_object_agg(event, n), '{}') from
                 (select event, count(*) n from quiz_events where created_at >= since group by event) t),
    'byMode',  (select coalesce(json_object_agg(coalesce(mode, 'n/a'), n), '{}') from
                 (select mode, count(*) n from quiz_events where event = 'complete' and created_at >= since group by mode) t),
    'byRace',  (select coalesce(json_object_agg(coalesce(race_id, 'gov only'), n), '{}') from
                 (select race_id, count(*) n from quiz_events where event = 'complete' and created_at >= since group by race_id) t),
    'bySource',(select coalesce(json_object_agg(coalesce(source, 'direct'), n), '{}') from
                 (select source, count(*) n from quiz_events where event = 'start' and created_at >= since group by source) t),
    'byDay',   (select coalesce(json_agg(json_build_object('day', d, 'starts', s, 'completes', c) order by d), '[]') from
                 (select date_trunc('day', created_at at time zone 'America/New_York')::date d,
                         count(*) filter (where event = 'start') s,
                         count(*) filter (where event = 'complete') c
                    from quiz_events where created_at >= since group by 1) t)
  );
end $$;

revoke all on function public.quiz_stats(timestamptz) from public, anon;
grant execute on function public.quiz_stats(timestamptz) to authenticated;

-- ── Add officers (edit emails, then run) ─────────────────────────────
-- insert into public.quiz_admins (email) values ('officer@example.org');
