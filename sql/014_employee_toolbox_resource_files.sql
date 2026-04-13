-- Employee Toolbox: support uploaded documents (files in app storage) alongside URL links.
-- Run in Supabase SQL after 013_employee_toolbox_links.sql.

BEGIN;

ALTER TABLE public.employee_toolbox_links
    ALTER COLUMN url DROP NOT NULL;

ALTER TABLE public.employee_toolbox_links
    ADD COLUMN IF NOT EXISTS resource_type text NOT NULL DEFAULT 'link';

UPDATE public.employee_toolbox_links
SET resource_type = 'link'
WHERE resource_type IS NULL OR btrim(resource_type) = '';

ALTER TABLE public.employee_toolbox_links
    ADD COLUMN IF NOT EXISTS file_name text,
    ADD COLUMN IF NOT EXISTS original_filename text,
    ADD COLUMN IF NOT EXISTS file_path text,
    ADD COLUMN IF NOT EXISTS content_type text;

ALTER TABLE public.employee_toolbox_links
    DROP CONSTRAINT IF EXISTS employee_toolbox_links_resource_chk;

ALTER TABLE public.employee_toolbox_links
    ADD CONSTRAINT employee_toolbox_links_resource_chk CHECK (
        resource_type IN ('link', 'file')
        AND (
            (
                resource_type = 'link'
                AND url IS NOT NULL
                AND btrim(url) <> ''
            )
            OR (
                resource_type = 'file'
                AND file_path IS NOT NULL
                AND btrim(file_path) <> ''
            )
        )
    );

COMMENT ON COLUMN public.employee_toolbox_links.resource_type IS
    'link = external URL; file = document stored via app storage (Supabase bucket or local).';
COMMENT ON COLUMN public.employee_toolbox_links.file_path IS
    'Storage object key (same pattern as asset_documents).';
COMMENT ON COLUMN public.employee_toolbox_links.file_name IS
    'Display name for the file (typically matches original filename).';
COMMENT ON COLUMN public.employee_toolbox_links.original_filename IS
    'Filename as uploaded by the user.';
COMMENT ON COLUMN public.employee_toolbox_links.content_type IS
    'MIME type used for upload and download.';

COMMIT;
