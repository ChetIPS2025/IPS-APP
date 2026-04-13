-- Add auto-style job numbers to public.jobs and backfill existing rows.
-- Run in Supabase SQL editor after prior migrations.

ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS job_number text;

-- Assign JOB-0001, JOB-0002, … only to rows still missing a number (stable order by id).
WITH need AS (
    SELECT id FROM public.jobs WHERE job_number IS NULL OR trim(job_number) = ''
),
numbered AS (
    SELECT
        id,
        'JOB-' || LPAD((ROW_NUMBER() OVER (ORDER BY id))::text, 4, '0') AS new_num
    FROM need
)
UPDATE public.jobs AS j
SET job_number = n.new_num
FROM numbered AS n
WHERE j.id = n.id;

-- Optional: prevent duplicate numbers (allows multiple NULLs only if any slipped through).
CREATE UNIQUE INDEX IF NOT EXISTS jobs_job_number_unique
    ON public.jobs (job_number)
    WHERE job_number IS NOT NULL AND trim(job_number) <> '';
