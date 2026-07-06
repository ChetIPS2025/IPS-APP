-- Rental Equipment Inspection module (checkout, daily, return).

create table if not exists public.rental_equipment_inspections (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.assets(id) on delete cascade,
  job_id uuid null references public.jobs(id) on delete set null,
  customer_id uuid null references public.customers(id) on delete set null,
  inspection_type text not null default 'checkout',
  status text not null default 'draft',
  general_condition text default '',
  checklist jsonb not null default '{}'::jsonb,
  notes text default '',
  damage_reported boolean not null default false,
  damage_description text default '',
  damage_location text default '',
  repair_recommendation text default '',
  fail_inspection boolean not null default false,
  pdf_path text default '',
  pdf_url text default '',
  performed_by_user_id uuid null,
  performed_by_name text default '',
  signed_at timestamptz null,
  completed_at timestamptz null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint rental_equipment_inspections_type_check
    check (inspection_type in ('checkout', 'daily', 'return')),
  constraint rental_equipment_inspections_status_check
    check (status in ('draft', 'complete', 'failed', 'exported'))
);

create index if not exists rental_equipment_insp_asset_idx
  on public.rental_equipment_inspections (asset_id, updated_at desc);

create index if not exists rental_equipment_insp_job_idx
  on public.rental_equipment_inspections (job_id, updated_at desc);

create index if not exists rental_equipment_insp_type_status_idx
  on public.rental_equipment_inspections (inspection_type, status, updated_at desc);

create table if not exists public.rental_equipment_inspection_photos (
  id uuid primary key default gen_random_uuid(),
  inspection_id uuid not null references public.rental_equipment_inspections(id) on delete cascade,
  slot_key text not null,
  photo_path text default '',
  photo_url text default '',
  uploaded_by uuid null,
  uploaded_at timestamptz not null default now()
);

create index if not exists rental_equipment_insp_photo_idx
  on public.rental_equipment_inspection_photos (inspection_id, slot_key);

create table if not exists public.rental_equipment_inspection_signatures (
  id uuid primary key default gen_random_uuid(),
  inspection_id uuid not null references public.rental_equipment_inspections(id) on delete cascade,
  role text not null,
  signer_name text default '',
  signature_data text default '',
  signed_at timestamptz null,
  constraint rental_equipment_insp_sig_role_check
    check (role in ('ips_employee', 'customer'))
);

create index if not exists rental_equipment_insp_sig_idx
  on public.rental_equipment_inspection_signatures (inspection_id, role);

alter table if exists public.rental_equipment_inspections enable row level security;
alter table if exists public.rental_equipment_inspection_photos enable row level security;
alter table if exists public.rental_equipment_inspection_signatures enable row level security;

drop policy if exists "Allow read access" on public.rental_equipment_inspections;
create policy "Allow read access" on public.rental_equipment_inspections
  for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.rental_equipment_inspections;
create policy "Allow insert access" on public.rental_equipment_inspections
  for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.rental_equipment_inspections;
create policy "Allow update access" on public.rental_equipment_inspections
  for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.rental_equipment_inspections;
create policy "Allow delete access" on public.rental_equipment_inspections
  for delete to authenticated using (true);

drop policy if exists "Allow read access" on public.rental_equipment_inspection_photos;
create policy "Allow read access" on public.rental_equipment_inspection_photos
  for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.rental_equipment_inspection_photos;
create policy "Allow insert access" on public.rental_equipment_inspection_photos
  for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.rental_equipment_inspection_photos;
create policy "Allow update access" on public.rental_equipment_inspection_photos
  for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.rental_equipment_inspection_photos;
create policy "Allow delete access" on public.rental_equipment_inspection_photos
  for delete to authenticated using (true);

drop policy if exists "Allow read access" on public.rental_equipment_inspection_signatures;
create policy "Allow read access" on public.rental_equipment_inspection_signatures
  for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.rental_equipment_inspection_signatures;
create policy "Allow insert access" on public.rental_equipment_inspection_signatures
  for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.rental_equipment_inspection_signatures;
create policy "Allow update access" on public.rental_equipment_inspection_signatures
  for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.rental_equipment_inspection_signatures;
create policy "Allow delete access" on public.rental_equipment_inspection_signatures
  for delete to authenticated using (true);
