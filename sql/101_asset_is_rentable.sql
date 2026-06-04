-- Rentable flag: assets that may appear in estimate / rental equipment pickers.
alter table public.assets
  add column if not exists is_rentable boolean not null default false;

comment on column public.assets.is_rentable is
  'When true, asset is available for rental equipment selection (e.g. build estimate).';

-- Preserve existing "rent to customer" markings as rentable for estimates.
update public.assets
set is_rentable = true
where is_rental = true
  and is_rentable = false;
