-- IPS Coupling Inspection Form V7 — parent table, child tables, and RLS.
-- Safe to run in Supabase SQL Editor even if 096 was not applied first.

create extension if not exists "pgcrypto";

-- 1. Parent table (must exist before child FKs and policies)
create table if not exists public.coupling_inspections (
  id uuid primary key default gen_random_uuid(),
  job_id uuid null references public.jobs(id) on delete set null,
  equipment_id uuid null references public.assets(id) on delete set null,
  customer_id uuid null references public.customers(id) on delete set null,
  coupling_model text not null default '1030G20',
  header jsonb not null default '{}'::jsonb,
  specs jsonb not null default '{}'::jsonb,
  torque_rows jsonb not null default '[]'::jsonb,
  inspection_fields jsonb not null default '{}'::jsonb,
  photo_attachments jsonb not null default '[]'::jsonb,
  technician_signature text default '',
  supervisor_signature text default '',
  customer_signature text default '',
  status text not null default 'draft',
  created_by uuid null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz null,
  constraint coupling_inspections_status_check
    check (status in ('draft', 'complete', 'exported'))
);

alter table public.coupling_inspections
  add column if not exists form_version text not null default 'V7';

comment on column public.coupling_inspections.form_version is 'IPS coupling inspection form version (V6, V7, …).';

create index if not exists coupling_insp_job_idx
  on public.coupling_inspections (job_id, updated_at desc);

create index if not exists coupling_insp_equipment_idx
  on public.coupling_inspections (equipment_id, updated_at desc);

create index if not exists coupling_insp_status_idx
  on public.coupling_inspections (status, updated_at desc);

-- 2. Child tables (after parent exists)
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

-- 3. Enable RLS (after all tables exist)
alter table public.coupling_inspections enable row level security;
alter table public.coupling_torque_checks enable row level security;
alter table public.coupling_inspection_photos enable row level security;
alter table public.coupling_inspection_signatures enable row level security;

-- 4. Policies (after RLS is enabled)
drop policy if exists "Allow all authenticated access" on public.coupling_inspections;
create policy "Allow all authenticated access" on public.coupling_inspections
  for all to authenticated using (true) with check (true);

drop policy if exists "Allow read access" on public.coupling_inspections;
drop policy if exists "Allow insert access" on public.coupling_inspections;
drop policy if exists "Allow update access" on public.coupling_inspections;
drop policy if exists "Allow delete access" on public.coupling_inspections;

drop policy if exists "Allow all authenticated access" on public.coupling_torque_checks;
create policy "Allow all authenticated access" on public.coupling_torque_checks
  for all to authenticated using (true) with check (true);

drop policy if exists "Allow read access" on public.coupling_torque_checks;
drop policy if exists "Allow insert access" on public.coupling_torque_checks;
drop policy if exists "Allow update access" on public.coupling_torque_checks;
drop policy if exists "Allow delete access" on public.coupling_torque_checks;

drop policy if exists "Allow all authenticated access" on public.coupling_inspection_photos;
create policy "Allow all authenticated access" on public.coupling_inspection_photos
  for all to authenticated using (true) with check (true);

drop policy if exists "Allow read access" on public.coupling_inspection_photos;
drop policy if exists "Allow insert access" on public.coupling_inspection_photos;
drop policy if exists "Allow update access" on public.coupling_inspection_photos;
drop policy if exists "Allow delete access" on public.coupling_inspection_photos;

drop policy if exists "Allow all authenticated access" on public.coupling_inspection_signatures;
create policy "Allow all authenticated access" on public.coupling_inspection_signatures
  for all to authenticated using (true) with check (true);

drop policy if exists "Allow read access" on public.coupling_inspection_signatures;
drop policy if exists "Allow insert access" on public.coupling_inspection_signatures;
drop policy if exists "Allow update access" on public.coupling_inspection_signatures;
drop policy if exists "Allow delete access" on public.coupling_inspection_signatures;
