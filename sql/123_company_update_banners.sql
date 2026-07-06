-- Optional banner images for company-wide announcements.
-- Safe to re-run.

alter table if exists public.company_updates
    add column if not exists banner_path text not null default '',
    add column if not exists banner_file_name text not null default '',
    add column if not exists banner_mime_type text not null default '',
    add column if not exists banner_caption text not null default '',
    add column if not exists banner_uploaded_at timestamptz;

comment on column public.company_updates.banner_path is
    'Storage object path for optional dashboard banner image (company_updates/...).';
comment on column public.company_updates.banner_caption is
    'Optional caption displayed below the banner image.';
