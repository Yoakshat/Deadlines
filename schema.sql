-- ── Run this in Supabase SQL Editor ───────────────────────────────────────────

create table if not exists classes (
  id           bigint generated always as identity primary key,
  name         text        not null unique,
  last_checked timestamptz,
  created_at   timestamptz not null default now()
);

create table if not exists assignments (
  id          bigint generated always as identity primary key,
  class       text        not null,
  title       text        not null,
  due_date    timestamp,
  type        text        not null default 'other',
  description text        not null default '',
  notified    boolean     not null default false,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),

  unique (class, title)
);

create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger assignments_updated_at
  before update on assignments
  for each row execute function update_updated_at();

create index if not exists idx_assignments_due_date on assignments (due_date);
create index if not exists idx_assignments_class    on assignments (class);

create or replace view due_today as
  select id, class, title, due_date, type, description
  from assignments
  where due_date::date = current_date
  order by due_date, class;
