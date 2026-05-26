-- =============================================================================
-- 091_item_image_paths.sql — Item photo fields (separate from QR codes)
-- Safe to re-run.
-- =============================================================================

alter table if exists public.pricing_guide_items
    add column if not exists image_path text not null default '',
    add column if not exists image_file_name text not null default '',
    add column if not exists image_mime_type text not null default '',
    add column if not exists image_uploaded_at timestamptz,
    add column if not exists image_uploaded_by text not null default '';

comment on column public.pricing_guide_items.image_path is
    'Storage object path for item photo (assets/item_images/pricing_guide/...). Not QR.';
comment on column public.pricing_guide_items.image_url is
    'Optional public HTTPS URL for item photo. Not QR.';
comment on column public.pricing_guide_items.qr_code_url is
    'Optional QR label/link URL. Separate from item photo.';

-- Ensure inventory/assets image columns exist (from 071/074; no-op if present).
alter table if exists public.inventory_items
    add column if not exists image_path text,
    add column if not exists image_url text,
    add column if not exists image_file_name text,
    add column if not exists image_mime_type text,
    add column if not exists image_uploaded_at timestamptz,
    add column if not exists image_uploaded_by uuid;

alter table if exists public.assets
    add column if not exists image_path text,
    add column if not exists image_url text,
    add column if not exists image_file_name text,
    add column if not exists image_mime_type text,
    add column if not exists image_uploaded_at timestamptz,
    add column if not exists image_uploaded_by uuid;
