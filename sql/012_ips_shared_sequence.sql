-- Shared Quote (QYY###) / Job (JYY###) sequence — one counter per UTC calendar year.
-- Run in Supabase SQL editor (or psql). Safe to re-run: counters only move up.
--
-- Format (app): Q + 2-digit year + 3-digit sequence, e.g. Q26208
--               J + same numeric tail when a job is linked to that quote, e.g. J26208
-- Standalone jobs consume the next sequence slot (e.g. J26209 after Q26208/J26208).

CREATE TABLE IF NOT EXISTS public.ips_yearly_sequence (
    year_yy smallint PRIMARY KEY CHECK (year_yy >= 0 AND year_yy <= 99),
    sequence_number bigint NOT NULL DEFAULT 0
);

COMMENT ON TABLE public.ips_yearly_sequence IS
    'Per-year last issued sequence index; ips_next_yearly_seq() increments atomically for quotes and jobs.';

-- Bootstrap from existing quote_number / job_number (current QYYNNN / JYYNNN and legacy formats).
DO $$
DECLARE
    current_yy smallint := (EXTRACT(YEAR FROM NOW())::int % 100)::smallint;
BEGIN
    INSERT INTO public.ips_yearly_sequence AS t (year_yy, sequence_number)
    SELECT yy, mx
    FROM (
        SELECT yy, MAX(seq) AS mx
        FROM (
            -- Current: QYYNNN / JYYNNN
            SELECT
                (substring(quote_number FROM 2 FOR 2))::smallint AS yy,
                (substring(quote_number FROM 4 FOR 3))::bigint AS seq
            FROM public.estimates
            WHERE quote_number ~* '^Q[0-9]{5}$'
            UNION ALL
            SELECT
                (substring(job_number FROM 2 FOR 2))::smallint,
                (substring(job_number FROM 4 FOR 3))::bigint
            FROM public.jobs
            WHERE job_number ~* '^J[0-9]{5}$'
            UNION ALL
            -- Legacy: Q + YY + 5-digit sequence (use trailing 3 digits as slot when possible)
            SELECT
                (substring(quote_number FROM 2 FOR 2))::smallint,
                (substring(quote_number FROM 4 FOR 3))::bigint
            FROM public.estimates
            WHERE quote_number ~* '^Q[0-9]{7}$'
            UNION ALL
            -- Legacy: Q + 5 digits (no year) — assign to current UTC year
            SELECT
                current_yy,
                (substring(quote_number FROM 2 FOR 5))::bigint
            FROM public.estimates
            WHERE quote_number ~* '^Q[0-9]{5}$'
              AND quote_number !~* '^Q[0-9]{2}[0-9]{3}$'
            UNION ALL
            -- Legacy: J + 5 digits (no year)
            SELECT
                current_yy,
                (substring(job_number FROM 2 FOR 5))::bigint
            FROM public.jobs
            WHERE job_number ~* '^J[0-9]{5}$'
              AND job_number !~* '^J[0-9]{2}[0-9]{3}$'
            UNION ALL
            -- Legacy: JOB-{digits}
            SELECT
                current_yy,
                (regexp_match(job_number, '^JOB-([0-9]+)$', 'i'))[1]::bigint
            FROM public.jobs
            WHERE job_number ~* '^JOB-[0-9]+$'
        ) parsed
        WHERE yy IS NOT NULL AND seq IS NOT NULL
        GROUP BY yy
    ) boot
    ON CONFLICT (year_yy) DO UPDATE SET
        sequence_number = GREATEST(t.sequence_number, EXCLUDED.sequence_number);

    -- Ensure current year row exists even when no historical numbers match.
    INSERT INTO public.ips_yearly_sequence (year_yy, sequence_number)
    VALUES (current_yy, 0)
    ON CONFLICT (year_yy) DO NOTHING;
END $$;

CREATE OR REPLACE FUNCTION public.ips_next_yearly_seq(p_year_yy smallint DEFAULT NULL)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    target_yy smallint := COALESCE(
        p_year_yy,
        (EXTRACT(YEAR FROM NOW())::int % 100)::smallint
    );
    n bigint;
BEGIN
    INSERT INTO public.ips_yearly_sequence (year_yy, sequence_number)
    VALUES (target_yy, 0)
    ON CONFLICT (year_yy) DO NOTHING;

    UPDATE public.ips_yearly_sequence
    SET sequence_number = sequence_number + 1
    WHERE year_yy = target_yy
    RETURNING sequence_number INTO n;

    IF n IS NULL THEN
        RAISE EXCEPTION 'ips_yearly_sequence row missing for year %', target_yy;
    END IF;

    RETURN n;
END;
$$;

COMMENT ON FUNCTION public.ips_next_yearly_seq(smallint) IS
    'Returns next 3-digit sequence integer for the given 2-digit year (or current UTC year). Format QYY### / JYY### in app.';

-- Backward-compatible alias used by older deployments / scripts.
CREATE OR REPLACE FUNCTION public.ips_next_job_quote_seq()
RETURNS bigint
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT public.ips_next_yearly_seq();
$$;

COMMENT ON FUNCTION public.ips_next_job_quote_seq() IS
    'Deprecated alias for ips_next_yearly_seq(); kept for backward compatibility.';

REVOKE ALL ON TABLE public.ips_yearly_sequence FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ips_next_yearly_seq() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ips_next_job_quote_seq() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.ips_next_yearly_seq() TO service_role;
GRANT EXECUTE ON FUNCTION public.ips_next_yearly_seq() TO postgres;
GRANT EXECUTE ON FUNCTION public.ips_next_job_quote_seq() TO service_role;
GRANT EXECUTE ON FUNCTION public.ips_next_job_quote_seq() TO postgres;

-- Legacy single-row counter (pre-yearly). Left in place if present; no longer used by app.
CREATE TABLE IF NOT EXISTS public.ips_shared_sequence (
    id smallint PRIMARY KEY CHECK (id = 1),
    sequence_number bigint NOT NULL DEFAULT 0
);
