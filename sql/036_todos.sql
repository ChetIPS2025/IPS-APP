-- Simple dashboard To-Do list
-- Table: public.todos

create table if not exists public.todos (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text,
  due_date date,
  priority text not null default 'Normal',
  status text not null default 'Open',
  assigned_to uuid references public.profiles(id),
  created_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

-- Enforce allowed values (keeps UI + data consistent)
alter table public.todos
  drop constraint if exists todos_priority_check,
  add constraint todos_priority_check check (priority in ('Low','Normal','High','Urgent'));

alter table public.todos
  drop constraint if exists todos_status_check,
  add constraint todos_status_check check (status in ('Open','In Progress','Complete'));

create index if not exists todos_status_due_idx on public.todos (status, due_date);
create index if not exists todos_assigned_to_idx on public.todos (assigned_to);

-- RLS: allow authenticated CRUD (matches project-wide posture in sql/019_rls_authenticated_crud.sql)
alter table if exists public.todos enable row level security;

drop policy if exists "Allow read access" on public.todos;
create policy "Allow read access" on public.todos for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.todos;
create policy "Allow insert access" on public.todos for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.todos;
create policy "Allow update access" on public.todos for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.todos;
create policy "Allow delete access" on public.todos for delete to authenticated using (true);

