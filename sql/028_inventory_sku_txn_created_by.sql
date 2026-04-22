-- SKU for scan fallback + created_by on inventory_transactions (additive; safe to re-run).
-- Run after sql/027_inventory_qr_and_transactions.sql.

alter table public.inventory_items
    add column if not exists sku text;

create index if not exists idx_inventory_items_sku_trim
    on public.inventory_items (lower(trim(sku)))
    where sku is not null and length(trim(sku)) > 0;

comment on column public.inventory_items.sku is 'Optional alternate scan / lookup code (not necessarily unique).';

alter table public.inventory_transactions
    add column if not exists created_by text;

comment on column public.inventory_transactions.created_by is 'Human-readable actor (e.g. profile email) at time of transaction.';
