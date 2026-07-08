-- Per-line invoice visibility for job cost ledger (run after 114_job_cost_transactions_extend.sql).

alter table if exists public.job_cost_transactions
    add column if not exists show_on_invoice boolean not null default true;

create index if not exists idx_job_cost_txn_show_on_invoice
    on public.job_cost_transactions (job_id, show_on_invoice);

comment on column public.job_cost_transactions.show_on_invoice is
    'When false, line remains in job cost but is excluded from customer invoice / T&M billing output.';
