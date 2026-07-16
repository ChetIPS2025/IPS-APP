-- =============================================================================
-- 133_small_hand_tools_images.sql — Photo fields for small hand tool thumbnails
-- Safe to re-run.
-- =============================================================================

alter table if exists public.small_hand_tools
    add column if not exists image_path text not null default '',
    add column if not exists image_url text not null default '',
    add column if not exists image_file_name text not null default '',
    add column if not exists image_mime_type text not null default '',
    add column if not exists image_uploaded_at timestamptz,
    add column if not exists image_uploaded_by text not null default '',
    add column if not exists image_status text not null default 'missing';

comment on column public.small_hand_tools.image_path is
    'Storage object path for tool photo (assets/item_images/small_hand_tools/...).';
comment on column public.small_hand_tools.image_status is
    'Photo review status: missing, needs_review, approved, rejected.';
