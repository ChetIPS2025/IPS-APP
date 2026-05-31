-- Allow coupling_inspections.task_id to reference IPS todos subjobs or job_tasks.
-- Run after sql/098_coupling_inspections_task_link.sql.

alter table public.coupling_inspections
    drop constraint if exists coupling_inspections_task_id_fkey;

comment on column public.coupling_inspections.task_id is
    'Linked subjob id: todos.id (Job Details subjobs) or job_tasks.id (field workflow).';

comment on column public.coupling_inspections.subjob_id is
    'Mirrors task_id for subjob linkage; supports todos and job_tasks ids.';
