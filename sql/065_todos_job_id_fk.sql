-- Ensure todos (IPS Tasks module) has job_id FK and status default.
-- Safe to run on databases that already applied 009_tasks_updates.sql or 062_phase3_operations_hub.sql.

alter table public.todos
    add column if not exists job_id uuid null;

alter table public.todos
    add column if not exists status text not null default 'Open';

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'todos_job_id_fkey'
          and conrelid = 'public.todos'::regclass
    ) then
        alter table public.todos
            add constraint todos_job_id_fkey
            foreign key (job_id) references public.jobs (id) on delete set null;
    end if;
exception
    when duplicate_object then null;
end $$;

create index if not exists idx_todos_job_id on public.todos (job_id);

-- Optional legacy alias table (no-op if missing)
alter table if exists public.tasks
    add column if not exists job_id uuid null;

alter table if exists public.tasks
    add column if not exists status text not null default 'Open';

do $$
begin
    if to_regclass('public.tasks') is not null
       and not exists (
           select 1
           from pg_constraint
           where conname = 'tasks_job_id_fkey'
             and conrelid = 'public.tasks'::regclass
       ) then
        alter table public.tasks
            add constraint tasks_job_id_fkey
            foreign key (job_id) references public.jobs (id) on delete set null;
    end if;
exception
    when duplicate_object then null;
end $$;
