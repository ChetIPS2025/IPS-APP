-- Optional capture metadata for job_task_photos (who saved + created_at already timestamps the row).
-- Run after sql/051_job_task_photos.sql.

alter table if exists public.job_task_photos
    add column if not exists captured_by_user_id text;

alter table if exists public.job_task_photos
    add column if not exists captured_by_name text;

comment on column public.job_task_photos.captured_by_user_id is 'IPS profile id when the photo was uploaded.';
comment on column public.job_task_photos.captured_by_name is 'Display name or email at upload time.';
