-- Merge ``hazard_number`` into ``task_number``, then drop ``hazard_number``.
-- Run once on existing databases that still have ``hazard_number`` (from sql/048).
-- Fresh installs using the updated 048 definition may never have the column; this script no-ops safely.

BEGIN;

DO $body$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns c
        WHERE c.table_schema = 'public'
          AND c.table_name = 'job_tasks'
          AND c.column_name = 'hazard_number'
    ) THEN
        UPDATE public.job_tasks AS j
        SET task_number = CASE
            WHEN NULLIF(TRIM(COALESCE(j.task_number, '')), '') IS NULL
                 AND NULLIF(TRIM(COALESCE(j.hazard_number, '')), '') IS NOT NULL
                THEN TRIM(j.hazard_number)
            WHEN NULLIF(TRIM(COALESCE(j.task_number, '')), '') IS NOT NULL
                 AND NULLIF(TRIM(COALESCE(j.hazard_number, '')), '') IS NULL
                THEN TRIM(j.task_number)
            WHEN TRIM(COALESCE(j.task_number, '')) = TRIM(COALESCE(j.hazard_number, ''))
                THEN TRIM(j.task_number)
            ELSE TRIM(j.task_number) || ' · ' || TRIM(j.hazard_number)
        END;

        ALTER TABLE public.job_tasks DROP COLUMN hazard_number;
    END IF;
END
$body$;

COMMENT ON TABLE public.job_tasks IS 'Discrete work items under a job; primary human label is task_number.';

COMMIT;
