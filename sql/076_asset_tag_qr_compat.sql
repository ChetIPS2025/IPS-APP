-- Asset tag + QR compatibility for legacy printed labels.
-- Safe to re-run.

alter table public.assets
    add column if not exists asset_tag text;

comment on column public.assets.asset_tag is 'Human-readable asset tag; defaults to asset_id when unset.';

-- Backfill tag from asset_id / asset_number where missing.
update public.assets
set asset_tag = coalesce(
    nullif(trim(asset_tag), ''),
    nullif(trim(asset_id), ''),
    nullif(trim(asset_number), '')
)
where coalesce(trim(asset_tag), '') = ''
  and (coalesce(trim(asset_id), '') <> '' or coalesce(trim(asset_number), '') <> '');

-- Mirror qr_code_value into qr_value when qr_value is empty (legacy labels).
update public.assets
set qr_value = qr_code_value
where coalesce(trim(qr_value), '') = ''
  and coalesce(trim(qr_code_value), '') <> '';
