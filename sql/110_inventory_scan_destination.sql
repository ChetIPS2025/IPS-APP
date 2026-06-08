-- Mobile QR scan destination: shop vs job (reports / audit).

alter table if exists public.inventory_transactions
    add column if not exists destination_type text null;

comment on column public.inventory_transactions.destination_type is
    'Mobile scan destination: shop (job_id null) or job (job_id set).';

alter table if exists public.job_materials
    add column if not exists destination_type text null;

comment on column public.job_materials.destination_type is
    'Costing destination: shop or job (job materials lines are job when job_id is set).';

create index if not exists idx_inventory_transactions_destination_type
    on public.inventory_transactions (destination_type)
    where destination_type is not null;
