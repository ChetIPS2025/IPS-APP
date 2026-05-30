-- IPS Coupling Inspection Form V7 — child tables and form version.

alter table if exists public.coupling_inspections
  add column if not exists form_version text not null default 'V7';

comment on column public.coupling_inspections.form_version is 'IPS coupling inspection form version (V6, V7, …).';

create table if not exists public.coupling_torque_checks (
  id uuid primary key default gen_random_uuid(),
  inspection_id uuid not null references public.coupling_inspections(id) on delete cascade,
  bolt_order integer not null,
  clock_position text not null,
  pass1_checked boolean not null default false,
  pass2_checked boolean not null default false,
  final_checked boolean not null default false,
  witness_initials text not null default '',
  pass_fail text null,
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint coupling_torque_checks_order_unique unique (inspection_id, bolt_order),
  constraint coupling_torque_checks_pass_fail_check
    check (pass_fail is null or pass_fail in ('pass', 'fail'))
);

create index if not exists coupling_torque_checks_insp_idx
  on public.coupling_torque_checks (inspection_id, bolt_order);

create table if not exists public.coupling_inspection_photos (
  id uuid primary key default gen_random_uuid(),
  inspection_id uuid not null references public.coupling_inspections(id) on delete cascade,
  category text not null,
  storage_path text not null default '',
  file_name text not null default '',
  caption text not null default '',
  uploaded_by text not null default '',
  uploaded_at timestamptz not null default now(),
  constraint coupling_insp_photos_category_check
    check (category in (
      'before_service',
      'coupling_teeth',
      'hub_gap',
      'grease_condition',
      'torque_verification',
      'witness_marks',
      'guard_installed',
      'final_condition'
    ))
);

create index if not exists coupling_insp_photos_insp_idx
  on public.coupling_inspection_photos (inspection_id, uploaded_at desc);

create table if not exists public.coupling_inspection_signatures (
  id uuid primary key default gen_random_uuid(),
  inspection_id uuid not null references public.coupling_inspections(id) on delete cascade,
  role text not null,
  signer_name text not null default '',
  signature_image text not null default '',
  signed_at timestamptz null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint coupling_insp_signatures_role_check
    check (role in ('technician', 'supervisor', 'customer_representative')),
  constraint coupling_insp_signatures_role_unique unique (inspection_id, role)
);

create index if not exists coupling_insp_signatures_insp_idx
  on public.coupling_inspection_signatures (inspection_id);

alter table if exists public.coupling_torque_checks enable row level security;
alter table if exists public.coupling_inspection_photos enable row level security;
alter table if exists public.coupling_inspection_signatures enable row level security;

drop policy if exists "Allow read access" on public.coupling_torque_checks;
create policy "Allow read access" on public.coupling_torque_checks
  for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.coupling_torque_checks;
create policy "Allow insert access" on public.coupling_torque_checks
  for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.coupling_torque_checks;
create policy "Allow update access" on public.coupling_torque_checks
  for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.coupling_torque_checks;
create policy "Allow delete access" on public.coupling_torque_checks
  for delete to authenticated using (true);

drop policy if exists "Allow read access" on public.coupling_inspection_photos;
create policy "Allow read access" on public.coupling_inspection_photos
  for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.coupling_inspection_photos;
create policy "Allow insert access" on public.coupling_inspection_photos
  for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.coupling_inspection_photos;
create policy "Allow update access" on public.coupling_inspection_photos
  for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.coupling_inspection_photos;
create policy "Allow delete access" on public.coupling_inspection_photos
  for delete to authenticated using (true);

drop policy if exists "Allow read access" on public.coupling_inspection_signatures;
create policy "Allow read access" on public.coupling_inspection_signatures
  for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.coupling_inspection_signatures;
create policy "Allow insert access" on public.coupling_inspection_signatures
  for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.coupling_inspection_signatures;
create policy "Allow update access" on public.coupling_inspection_signatures
  for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.coupling_inspection_signatures;
create policy "Allow delete access" on public.coupling_inspection_signatures
  for delete to authenticated using (true);
