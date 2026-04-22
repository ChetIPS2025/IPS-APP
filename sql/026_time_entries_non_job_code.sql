-- Non-job time categories (PM grid): nullable job_id + non_job_code; job costing uses job rows only.

ALTER TABLE public.time_entries
    ADD COLUMN IF NOT EXISTS non_job_code text;

ALTER TABLE public.time_entries
    ALTER COLUMN job_id DROP NOT NULL;

DROP INDEX IF EXISTS uq_time_entries_employee_job_day;

-- One row per employee × job × day (job work)
CREATE UNIQUE INDEX IF NOT EXISTS uq_time_entries_emp_job_day
    ON public.time_entries (employee_id, job_id, work_date)
    WHERE job_id IS NOT NULL;

-- One row per employee × day × non-job category
CREATE UNIQUE INDEX IF NOT EXISTS uq_time_entries_emp_nonjob_day
    ON public.time_entries (employee_id, work_date, non_job_code)
    WHERE job_id IS NULL
      AND non_job_code IS NOT NULL
      AND btrim(non_job_code) <> '';

ALTER TABLE public.time_entries DROP CONSTRAINT IF EXISTS time_entries_job_xor_nonjob_chk;
ALTER TABLE public.time_entries ADD CONSTRAINT time_entries_job_xor_nonjob_chk CHECK (
    (job_id IS NOT NULL AND (non_job_code IS NULL OR btrim(non_job_code) = ''))
    OR
    (job_id IS NULL AND non_job_code IS NOT NULL AND btrim(non_job_code) <> '')
);

COMMENT ON COLUMN public.time_entries.non_job_code IS
    'Non-job bucket (SHOP, ADMIN, …) when job_id is null; mutually exclusive with job_id.';
