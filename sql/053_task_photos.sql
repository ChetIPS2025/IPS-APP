-- Task photos in dedicated Storage bucket ``task-photos`` (create bucket in Supabase + set policies).
-- Object keys: {job_id}/{task_id}/{timestamp}.jpg (app-generated).
-- Run after sql/051_job_task_photos.sql (legacy ``job_task_photos`` may still exist for old rows).

create table if not exists public.task_photos (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null references public.job_tasks (id) on delete cascade,
    job_id uuid not null references public.jobs (id) on delete cascade,
    photo_type text not null,
    file_url text not null,
    content_type text not null default 'image/jpeg',
    uploaded_by text,
    created_at timestamptz not null default now(),
    constraint task_photos_type_check check (photo_type in ('before', 'after', 'progress'))
);

create unique index if not exists uq_task_photos_task_before on public.task_photos (task_id)
    where photo_type = 'before';
create unique index if not exists uq_task_photos_task_after on public.task_photos (task_id)
    where photo_type = 'after';

create index if not exists idx_task_photos_task_id on public.task_photos (task_id);
create index if not exists idx_task_photos_job_id on public.task_photos (job_id);
create index if not exists idx_task_photos_created_at on public.task_photos (created_at desc);

comment on table public.task_photos is 'Task images; file_url is object key inside Storage bucket task-photos.';

alter table if exists public.task_photos enable row level security;
drop policy if exists "task_photos read" on public.task_photos;
create policy "task_photos read" on public.task_photos for select to authenticated using (true);
drop policy if exists "task_photos insert" on public.task_photos;
create policy "task_photos insert" on public.task_photos for insert to authenticated with check (true);
drop policy if exists "task_photos update" on public.task_photos;
create policy "task_photos update" on public.task_photos for update to authenticated using (true) with check (true);
drop policy if exists "task_photos delete" on public.task_photos;
create policy "task_photos delete" on public.task_photos for delete to authenticated using (true);
