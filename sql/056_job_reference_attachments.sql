-- Job reference attachments: PM/admin uploads (drawings, PDFs, photos) visible to supervisors in Work & Plan.
-- 1) Run this migration in Supabase SQL.
-- 2) Create Storage bucket: job-reference-attachments (public read optional; app uses service role + signed URLs).
-- 3) Add storage policies allowing authenticated upload if you use user-scoped uploads (or rely on service role from app).

BEGIN;

CREATE TABLE IF NOT EXISTS public.job_reference_attachments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id uuid NOT NULL REFERENCES public.jobs (id) ON DELETE CASCADE,
    task_id uuid NULL REFERENCES public.job_tasks (id) ON DELETE CASCADE,
    file_name text NOT NULL,
    file_type text NOT NULL DEFAULT 'application/octet-stream',
    -- Storage object path within bucket ``job-reference-attachments`` (not a public URL).
    file_url text NOT NULL,
    uploaded_by uuid NULL REFERENCES public.profiles (id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_job_reference_attachments_job_id
    ON public.job_reference_attachments (job_id);
CREATE INDEX IF NOT EXISTS idx_job_reference_attachments_task_id
    ON public.job_reference_attachments (task_id);
CREATE INDEX IF NOT EXISTS idx_job_reference_attachments_created_at
    ON public.job_reference_attachments (created_at DESC);

COMMENT ON TABLE public.job_reference_attachments IS
    'Reference files for a job or specific task; stored in Storage bucket job-reference-attachments.';
COMMENT ON COLUMN public.job_reference_attachments.file_url IS
    'Object key/path inside the job-reference-attachments bucket; signed URLs generated at read time.';

ALTER TABLE public.job_reference_attachments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow read access" ON public.job_reference_attachments;
CREATE POLICY "Allow read access" ON public.job_reference_attachments
    FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Allow insert access" ON public.job_reference_attachments;
CREATE POLICY "Allow insert access" ON public.job_reference_attachments
    FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "Allow update access" ON public.job_reference_attachments;
CREATE POLICY "Allow update access" ON public.job_reference_attachments
    FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow delete access" ON public.job_reference_attachments;
CREATE POLICY "Allow delete access" ON public.job_reference_attachments
    FOR DELETE TO authenticated USING (true);

COMMIT;
