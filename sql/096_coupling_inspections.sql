-- Coupling Inspection & Torque Verification records (IPS V6 digital form).

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

create index if not exists coupling_insp_job_idx
  on public.coupling_inspections (job_id, updated_at desc);

create index if not exists coupling_insp_equipment_idx
  on public.coupling_inspections (equipment_id, updated_at desc);

create index if not exists coupling_insp_status_idx
  on public.coupling_inspections (status, updated_at desc);

alter table if exists public.coupling_inspections enable row level security;

drop policy if exists "Allow read access" on public.coupling_inspections;
create policy "Allow read access" on public.coupling_inspections
  for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.coupling_inspections;
create policy "Allow insert access" on public.coupling_inspections
  for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.coupling_inspections;
create policy "Allow update access" on public.coupling_inspections
  for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.coupling_inspections;
create policy "Allow delete access" on public.coupling_inspections
  for delete to authenticated using (true);
