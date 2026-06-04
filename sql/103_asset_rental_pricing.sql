-- Rental pricing defaults for rentable assets (estimate Add Equipment).

alter table public.assets
  add column if not exists rental_rate_unit text default 'Days';

alter table public.assets
  add column if not exists rental_default_markup_percent numeric(8, 2) not null default 0;

comment on column public.assets.rental_rate_unit is
  'Unit for the primary rental rate: Hours, Days, or Weeks (estimate equipment).';

comment on column public.assets.rental_default_markup_percent is
  'Default markup percent when this asset is added to an estimate as equipment.';
