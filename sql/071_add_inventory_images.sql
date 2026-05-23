-- Inventory item image metadata (Supabase Storage bucket: inventory-images).
--
-- Setup notes:
-- 1. Create a private Storage bucket named `inventory-images` in Supabase.
-- 2. Configure bucket RLS/policies when ready (TODO).
-- 3. App uses signed URLs for thumbnails and detail previews.

alter table public.inventory_items
    add column if not exists image_path text,
    add column if not exists image_url text,
    add column if not exists image_file_name text,
    add column if not exists image_mime_type text,
    add column if not exists image_uploaded_at timestamptz,
    add column if not exists image_uploaded_by uuid;

alter table public.inventory_items
    add column if not exists updated_at timestamptz default now();

comment on column public.inventory_items.image_path is
    'Storage object path in inventory-images bucket (e.g. inventory-images/<id>/<file>).';
comment on column public.inventory_items.image_url is
    'Optional public HTTPS URL or legacy storage path fallback.';
