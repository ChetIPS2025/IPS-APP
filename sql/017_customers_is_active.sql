-- Active flag for customer companies (used by Customers UI: add/edit/deactivate).
-- Safe to re-run.

alter table public.customers
    add column if not exists is_active boolean not null default true;

comment on column public.customers.is_active is 'When false, customer is hidden or treated as inactive in workflows.';
