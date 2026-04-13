-- Rental flags and optional rate fields on assets (non-breaking: defaults preserve existing rows).
alter table public.assets add column if not exists is_rental boolean not null default false;

alter table public.assets add column if not exists rental_daily_rate numeric(12, 2);
alter table public.assets add column if not exists rental_weekly_rate numeric(12, 2);
alter table public.assets add column if not exists rental_monthly_rate numeric(12, 2);
alter table public.assets add column if not exists rental_notes text default '';

comment on column public.assets.is_rental is 'When true, asset may be rented to customers.';
comment on column public.assets.rental_daily_rate is 'Optional daily rental rate.';
comment on column public.assets.rental_weekly_rate is 'Optional weekly rental rate.';
comment on column public.assets.rental_monthly_rate is 'Optional monthly rental rate.';
comment on column public.assets.rental_notes is 'Notes for rental pricing or terms.';
