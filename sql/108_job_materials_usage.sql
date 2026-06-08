-- Job materials usage tracking: link costing lines to inventory txns, subjobs, and employees.

alter table if exists public.job_materials
    add column if not exists subjob_id uuid null,
    add column if not exists employee_id uuid null,
    add column if not exists inventory_transaction_id uuid null,
    add column if not exists used_at timestamptz null default now(),
    add column if not exists usage_source text not null default 'manual';

create index if not exists idx_job_materials_subjob_id on public.job_materials (subjob_id);
create index if not exists idx_job_materials_employee_id on public.job_materials (employee_id);
create index if not exists idx_job_materials_inv_txn_id on public.job_materials (inventory_transaction_id);

comment on column public.job_materials.subjob_id is 'Optional IPS subjob (todos.id) or field task id.';
comment on column public.job_materials.usage_source is 'qr_scan | manual_inventory | manual_entry';

alter table if exists public.inventory_transactions
    add column if not exists subjob_id uuid null;

create index if not exists idx_inventory_transactions_subjob_id on public.inventory_transactions (subjob_id);
