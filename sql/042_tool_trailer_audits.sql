-- Tool Trailer Audits: periodic random photo verification of kit items.

create table if not exists public.tool_trailer_audits (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.assets(id) on delete cascade,
  audit_period_start date not null,
  audit_period_end date not null,
  frequency text not null default 'Monthly',
  assigned_to_employee_id uuid null references public.employees(id) on delete set null,
  status text not null default 'Pending',
  created_at timestamptz not null default now(),
  due_date date not null,
  completed_at timestamptz,
  notes text default ''
);

create index if not exists tta_asset_idx on public.tool_trailer_audits (asset_id, due_date desc);
create index if not exists tta_status_idx on public.tool_trailer_audits (status, due_date);
create index if not exists tta_assignee_idx on public.tool_trailer_audits (assigned_to_employee_id, due_date desc);

alter table if exists public.tool_trailer_audits enable row level security;

drop policy if exists "Allow read access" on public.tool_trailer_audits;
create policy "Allow read access" on public.tool_trailer_audits for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.tool_trailer_audits;
create policy "Allow insert access" on public.tool_trailer_audits for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.tool_trailer_audits;
create policy "Allow update access" on public.tool_trailer_audits for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.tool_trailer_audits;
create policy "Allow delete access" on public.tool_trailer_audits for delete to authenticated using (true);

create table if not exists public.tool_trailer_audit_items (
  id uuid primary key default gen_random_uuid(),
  audit_id uuid not null references public.tool_trailer_audits(id) on delete cascade,
  kit_item_id uuid not null references public.asset_kit_items(id) on delete restrict,
  item_name text not null,
  required_quantity numeric(12,2) not null default 1,
  verified_quantity numeric(12,2),
  photo_url text default '',
  status text not null default 'Pending',
  notes text default '',
  verified_at timestamptz
);

create index if not exists ttai_audit_idx on public.tool_trailer_audit_items (audit_id);
create index if not exists ttai_status_idx on public.tool_trailer_audit_items (status);

alter table if exists public.tool_trailer_audit_items enable row level security;

drop policy if exists "Allow read access" on public.tool_trailer_audit_items;
create policy "Allow read access" on public.tool_trailer_audit_items for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.tool_trailer_audit_items;
create policy "Allow insert access" on public.tool_trailer_audit_items for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.tool_trailer_audit_items;
create policy "Allow update access" on public.tool_trailer_audit_items for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.tool_trailer_audit_items;
create policy "Allow delete access" on public.tool_trailer_audit_items for delete to authenticated using (true);

