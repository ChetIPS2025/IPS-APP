-- Allow job photos/documents to link to IPS todos subjobs (Job Details) or job_tasks.
-- Run after sql/061_field_operations_phase1.sql and sql/008_documents.sql.

alter table public.job_photos
    drop constraint if exists job_photos_task_id_fkey;

comment on column public.job_photos.task_id is
    'Optional subjob link: todos.id (Job Details) or job_tasks.id (field workflow). Null = job-level photo.';

create index if not exists idx_job_photos_task_id
    on public.job_photos (task_id);

alter table public.documents_hub
    add column if not exists task_id uuid null;

comment on column public.documents_hub.task_id is
    'Optional subjob link when linked_module is jobs. Null = job-level document.';

create index if not exists idx_documents_hub_task_id
    on public.documents_hub (task_id);

create index if not exists idx_documents_hub_job_task
    on public.documents_hub (linked_record_id, task_id);
