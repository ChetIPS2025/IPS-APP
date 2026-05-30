-- Link coupling inspections to job task / subjob work items.
-- Run after sql/096_coupling_inspections.sql and sql/048_job_tasks_planning_links.sql.

alter table public.coupling_inspections
add column if not exists job_id uuid null,
add column if not exists task_id uuid null,
add column if not exists subjob_id uuid null,
add column if not exists subjob_name text null,
add column if not exists task_title text null,
add column if not exists linked_task_status text null;

do $$
begin
    if exists (
        select 1
        from information_schema.tables
        where table_schema = 'public'
          and table_name = 'tasks'
    ) then
        begin
            alter table public.coupling_inspections
            add constraint coupling_inspections_task_id_fkey
            foreign key (task_id)
            references public.tasks (id)
            on delete set null;
        exception
            when duplicate_object then null;
        end;
    elsif exists (
        select 1
        from information_schema.tables
        where table_schema = 'public'
          and table_name = 'job_tasks'
    ) then
        begin
            alter table public.coupling_inspections
            add constraint coupling_inspections_task_id_fkey
            foreign key (task_id)
            references public.job_tasks (id)
            on delete set null;
        exception
            when duplicate_object then null;
        end;
    end if;
end $$;

create index if not exists idx_coupling_inspections_job_id
    on public.coupling_inspections (job_id);

create index if not exists idx_coupling_inspections_task_id
    on public.coupling_inspections (task_id);

create index if not exists idx_coupling_inspections_subjob_id
    on public.coupling_inspections (subjob_id);

comment on column public.coupling_inspections.task_id is
    'Linked job task / subjob (job_tasks.id in field workflow).';
comment on column public.coupling_inspections.subjob_id is
    'Optional subjob identifier; mirrors task_id when task rows represent subjobs.';
comment on column public.coupling_inspections.subjob_name is
    'Display label for linked subjob (typically job_tasks.task_number).';
comment on column public.coupling_inspections.task_title is
    'Human-readable task title snapshot at link time.';
comment on column public.coupling_inspections.linked_task_status is
    'Task status snapshot when inspection was linked or last saved.';
