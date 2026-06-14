-- Extend job_cost_transactions for full ledger linkage (run after 113_job_cost_transactions.sql).

alter table if exists public.job_cost_transactions
    add column if not exists asset_id uuid null references public.assets (id) on delete set null;

alter table if exists public.job_cost_transactions
    add column if not exists inventory_item_id uuid null references public.inventory_items (id) on delete set null;

alter table if exists public.job_cost_transactions
    add column if not exists description text not null default '';

alter table if exists public.job_cost_transactions
    add column if not exists created_by uuid null;

create index if not exists idx_job_cost_txn_asset_id on public.job_cost_transactions (asset_id);
create index if not exists idx_job_cost_txn_inventory_item_id on public.job_cost_transactions (inventory_item_id);
create index if not exists idx_job_cost_txn_source_type on public.job_cost_transactions (source_type);

comment on column public.job_cost_transactions.description is
    'Human-readable line description; item_name retained for backward compatibility.';

comment on column public.job_cost_transactions.cost_category is
    'labor | material | equipment | subcontract | rental | other';
