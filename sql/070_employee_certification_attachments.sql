-- Certification attachment metadata (Supabase Storage: certification-documents bucket).
--
-- Setup notes:
-- 1. Create a private Storage bucket named `certification-documents` in Supabase.
-- 2. Configure RLS/policies on the bucket when ready (TODO).
-- 3. App uses signed URLs for viewing; do not expose service role keys in the UI.

alter table public.employee_certifications
    add column if not exists attachment_path text,
    add column if not exists attachment_url text,
    add column if not exists attachment_file_name text,
    add column if not exists attachment_mime_type text,
    add column if not exists attachment_uploaded_at timestamptz,
    add column if not exists attachment_uploaded_by uuid;

alter table public.employee_certifications
    add column if not exists updated_at timestamptz default now();

update public.employee_certifications
set attachment_path = coalesce(attachment_path, '')
where attachment_path is null;
