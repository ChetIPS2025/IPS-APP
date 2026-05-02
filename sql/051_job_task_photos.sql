-- Task photos (before / after / progress) + job-level daily review progress shots.
-- Run after sql/050_job_daily_work_plan_and_review_photo.sql.

create table if not exists public.job_task_photos (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null references public.job_tasks (id) on delete cascade,
    photo_type text not null,
    storage_path text not null,
    content_type text not null default 'image/jpeg',
    created_at timestamptz not null default now(),
    constraint job_task_photos_type_check check (photo_type in ('before', 'after', 'progress'))
);

-- At most one current before and one current after per task (replace = delete + insert in app).
create unique index if not exists uq_job_task_photos_task_before on public.job_task_photos (task_id)
    where photo_type = 'before';
create unique index if not exists uq_job_task_photos_task_after on public.job_task_photos (task_id)
    where photo_type = 'after';

create index if not exists idx_job_task_photos_task_id on public.job_task_photos (task_id);
create index if not exists idx_job_task_photos_created_at on public.job_task_photos (created_at desc);

comment on table public.job_task_photos is 'Compressed images in storage; storage_path is the bucket key (signed URL in UI).';

create table if not exists public.job_daily_review_progress_photos (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    review_date date not null,
    slot smallint not null,
    storage_path text not null,
    content_type text not null default 'image/jpeg',
    created_at timestamptz not null default now(),
    constraint job_daily_review_progress_photos_slot_check check (slot >= 1 and slot <= 3),
    constraint uq_job_daily_review_progress_slot unique (job_id, review_date, slot)
);

create index if not exists idx_job_daily_review_progress_job_date on public.job_daily_review_progress_photos (job_id, review_date);

comment on table public.job_daily_review_progress_photos is 'Up to three general progress photos per job per review day.';

alter table if exists public.job_task_photos enable row level security;
drop policy if exists "Allow read access" on public.job_task_photos;
create policy "Allow read access" on public.job_task_photos for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.job_task_photos;
create policy "Allow insert access" on public.job_task_photos for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.job_task_photos;
create policy "Allow update access" on public.job_task_photos for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.job_task_photos;
create policy "Allow delete access" on public.job_task_photos for delete to authenticated using (true);

alter table if exists public.job_daily_review_progress_photos enable row level security;
drop policy if exists "Allow read access" on public.job_daily_review_progress_photos;
create policy "Allow read access" on public.job_daily_review_progress_photos for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.job_daily_review_progress_photos;
create policy "Allow insert access" on public.job_daily_review_progress_photos for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.job_daily_review_progress_photos;
create policy "Allow update access" on public.job_daily_review_progress_photos for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.job_daily_review_progress_photos;
create policy "Allow delete access" on public.job_daily_review_progress_photos for delete to authenticated using (true);
