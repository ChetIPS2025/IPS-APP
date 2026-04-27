-- Asset repair / expense tracking (works for any asset, including Tool Trailers)

create table if not exists public.asset_expenses (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.assets(id) on delete cascade,
  expense_type text not null default 'Other',
  expense_date date not null default (now()::date),
  vendor text default '',
  description text default '',
  amount numeric(12,2) not null default 0,
  receipt_url text default '',
  odometer_hours numeric(12,2),
  created_by uuid null references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  notes text default ''
);

alter table public.asset_expenses
  drop constraint if exists asset_expenses_type_check,
  add constraint asset_expenses_type_check check (
    expense_type in ('Repair','Maintenance','Parts','Fuel','Inspection','Registration','Other')
  );

create index if not exists asset_expenses_asset_date_idx on public.asset_expenses (asset_id, expense_date desc);
create index if not exists asset_expenses_type_idx on public.asset_expenses (expense_type);

alter table if exists public.asset_expenses enable row level security;

drop policy if exists "Allow read access" on public.asset_expenses;
create policy "Allow read access" on public.asset_expenses for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.asset_expenses;
create policy "Allow insert access" on public.asset_expenses for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.asset_expenses;
create policy "Allow update access" on public.asset_expenses for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.asset_expenses;
create policy "Allow delete access" on public.asset_expenses for delete to authenticated using (true);

