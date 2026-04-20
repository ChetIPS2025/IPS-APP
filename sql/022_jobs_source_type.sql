-- How the job row was created: costing / time / expenses use jobs.id (job_id on child rows).
-- Estimates remain quotes/proposals; converted jobs keep estimate_id and source_type = 'estimate'.

ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS source_type text;

UPDATE public.jobs
SET source_type = CASE
    WHEN estimate_id IS NOT NULL THEN 'estimate'
    ELSE 'standalone'
END
WHERE source_type IS NULL OR trim(source_type) = '';

COMMENT ON COLUMN public.jobs.source_type IS
    'estimate | standalone — estimate-linked vs direct Job Database create; financial actuals use job id.';
