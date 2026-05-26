-- =============================================================================
-- 092_item_image_status.sql — Image review status (missing / needs_review / approved / rejected)
-- Safe to re-run.
-- =============================================================================

alter table if exists public.pricing_guide_items
    add column if not exists image_status text not null default 'missing';

alter table if exists public.inventory_items
    add column if not exists image_status text not null default 'missing';

alter table if exists public.assets
    add column if not exists image_status text not null default 'missing';

-- Backfill: existing stored photos were auto-assigned and need human review.
update public.pricing_guide_items
set image_status = 'needs_review'
where coalesce(image_path, '') <> '' or coalesce(image_url, '') <> '';

update public.inventory_items
set image_status = 'needs_review'
where coalesce(image_path, '') <> '' or coalesce(image_url, '') <> '';

update public.assets
set image_status = 'needs_review'
where coalesce(image_path, '') <> '' or coalesce(image_url, '') <> '';

comment on column public.pricing_guide_items.image_status is
    'Item photo workflow: missing | needs_review | approved | rejected. Only approved photos display in catalog UI.';
