-- Atomic shared counter for Quote (Q#####) and Job (J#####) numbers.
-- Run in Supabase SQL editor (or psql). Safe to re-run: row is upserted; counter only moves up.

CREATE TABLE IF NOT EXISTS public.ips_shared_sequence (
    id smallint PRIMARY KEY CHECK (id = 1),
    sequence_number bigint NOT NULL DEFAULT 0
);

COMMENT ON TABLE public.ips_shared_sequence IS
    'Single-row counter: last issued sequence index; ips_next_job_quote_seq() increments atomically.';

-- Bootstrap from existing quote_number / job_number (same parsing rules as the app).
DO $$
DECLARE
    mx bigint;
BEGIN
    SELECT COALESCE(MAX(v), 0) INTO mx
    FROM (
        SELECT (substring(quote_number FROM 2 FOR 5))::bigint AS v
        FROM public.estimates
        WHERE quote_number ~* '^Q[0-9]{5}$'
        UNION ALL
        SELECT (substring(job_number FROM 2 FOR 5))::bigint AS v
        FROM public.jobs
        WHERE job_number ~* '^J[0-9]{5}$'
        UNION ALL
        SELECT (regexp_match(job_number, '^JOB-([0-9]+)$', 'i'))[1]::bigint AS v
        FROM public.jobs
        WHERE job_number ~* '^JOB-[0-9]+$'
    ) s;

    INSERT INTO public.ips_shared_sequence AS t (id, sequence_number)
    VALUES (1, mx)
    ON CONFLICT (id) DO UPDATE SET
        sequence_number = GREATEST(t.sequence_number, EXCLUDED.sequence_number);
END $$;

CREATE OR REPLACE FUNCTION public.ips_next_job_quote_seq()
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    n bigint;
BEGIN
    UPDATE public.ips_shared_sequence
    SET sequence_number = sequence_number + 1
    WHERE id = 1
    RETURNING sequence_number INTO n;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'ips_shared_sequence row missing; run sql/012_ips_shared_sequence.sql';
    END IF;

    RETURN n;
END;
$$;

COMMENT ON FUNCTION public.ips_next_job_quote_seq() IS
    'Returns next sequence integer (thread-safe under concurrent calls). Format as Q##### or J##### in app.';

REVOKE ALL ON TABLE public.ips_shared_sequence FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ips_next_job_quote_seq() FROM PUBLIC;

-- Supabase roles used by PostgREST / service role key
GRANT EXECUTE ON FUNCTION public.ips_next_job_quote_seq() TO service_role;
GRANT EXECUTE ON FUNCTION public.ips_next_job_quote_seq() TO postgres;
