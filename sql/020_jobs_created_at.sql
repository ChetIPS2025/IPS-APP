-- Optional: add created_at to jobs for ordering / auditing if the column is missing.
alter table if exists public.jobs
    add column if not exists created_at timestamptz default now();

-- Backfill nulls (defensive)
update public.jobs
set created_at = coalesce(created_at, now())
where created_at is null;
