-- Optional one-time migration: copy legacy equipment_catalog rows into assets as Equipment + rental rates.
-- Prerequisites: run 006_assets_rental.sql first. Table public.equipment_catalog must exist with compatible columns.
--
-- Expected equipment_catalog columns (from app): equipment_item, daily_rate, weekly_rate, monthly_rate, notes, is_active
--
-- Skips rows whose asset_name already matches (case-insensitive) an asset with category Equipment.

insert into public.assets (
    asset_id,
    asset_name,
    asset_type,
    category,
    subcategory,
    status,
    condition,
    location,
    notes,
    is_active,
    is_rental,
    rental_daily_rate,
    rental_weekly_rate,
    rental_monthly_rate,
    rental_notes,
    qr_code_value
)
select
    eq_cat_id,
    trim(e.equipment_item),
    'Other',
    'Equipment',
    '',
    'Available',
    '',
    '',
    '',
    coalesce(e.is_active, true),
    true,
    nullif(e.daily_rate, 0),
    nullif(e.weekly_rate, 0),
    nullif(e.monthly_rate, 0),
    coalesce(nullif(trim(e.notes), ''), ''),
    'IPS-' || eq_cat_id
from (
    select
        *,
        ('EQCAT-' || substr(md5(trim(coalesce(equipment_item, ''))), 1, 10)) as eq_cat_id
    from public.equipment_catalog
) e
where trim(coalesce(e.equipment_item, '')) <> ''
  and not exists (
    select 1
    from public.assets a
    where lower(trim(coalesce(a.category, ''))) = 'equipment'
      and lower(trim(coalesce(a.asset_name, ''))) = lower(trim(e.equipment_item))
  );
