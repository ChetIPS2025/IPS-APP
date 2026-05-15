-- Company-wide announcements (not tied to jobs).
-- Run in Supabase after prior migrations.

create table if not exists public.company_updates (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  message text not null,
  category text not null default 'General',
  priority text not null default 'Normal',
  posted_by uuid references public.profiles (id) on delete set null,
  attachment_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  expires_at timestamptz,
  is_active boolean not null default true
);

alter table public.company_updates
  drop constraint if exists company_updates_category_check,
  add constraint company_updates_category_check check (
    category in (
      'General',
      'Safety',
      'Schedule',
      'Policy',
      'Equipment',
      'HR / Payroll',
      'Training',
      'Urgent'
    )
  );

alter table public.company_updates
  drop constraint if exists company_updates_priority_check,
  add constraint company_updates_priority_check check (
    priority in ('Normal', 'Important', 'Urgent')
  );

create index if not exists company_updates_created_at_idx on public.company_updates (created_at desc);
create index if not exists company_updates_active_idx on public.company_updates (is_active);

create table if not exists public.company_update_reads (
  id uuid primary key default gen_random_uuid(),
  update_id uuid not null references public.company_updates (id) on delete cascade,
  user_id uuid not null references public.profiles (id) on delete cascade,
  read_at timestamptz not null default now(),
  constraint company_update_reads_update_user_unique unique (update_id, user_id)
);

create index if not exists company_update_reads_user_idx on public.company_update_reads (user_id);

alter table public.company_updates enable row level security;
alter table public.company_update_reads enable row level security;

drop policy if exists "company_updates_select_auth" on public.company_updates;
create policy "company_updates_select_auth"
  on public.company_updates for select
  to authenticated
  using (true);

drop policy if exists "company_updates_insert_office" on public.company_updates;
create policy "company_updates_insert_office"
  on public.company_updates for insert
  to authenticated
  with check (
    exists (
      select 1
      from public.profiles p
      where p.id = auth.uid()
        and lower(coalesce(trim(p.role), '')) in ('admin', 'manager')
    )
  );

drop policy if exists "company_updates_update_office" on public.company_updates;
create policy "company_updates_update_office"
  on public.company_updates for update
  to authenticated
  using (
    exists (
      select 1
      from public.profiles p
      where p.id = auth.uid()
        and lower(coalesce(trim(p.role), '')) in ('admin', 'manager')
    )
  )
  with check (
    exists (
      select 1
      from public.profiles p
      where p.id = auth.uid()
        and lower(coalesce(trim(p.role), '')) in ('admin', 'manager')
    )
  );

drop policy if exists "company_updates_delete_office" on public.company_updates;
create policy "company_updates_delete_office"
  on public.company_updates for delete
  to authenticated
  using (
    exists (
      select 1
      from public.profiles p
      where p.id = auth.uid()
        and lower(coalesce(trim(p.role), '')) in ('admin', 'manager')
    )
  );

drop policy if exists "company_update_reads_select_own" on public.company_update_reads;
create policy "company_update_reads_select_own"
  on public.company_update_reads for select
  to authenticated
  using (user_id = auth.uid());

drop policy if exists "company_update_reads_insert_own" on public.company_update_reads;
create policy "company_update_reads_insert_own"
  on public.company_update_reads for insert
  to authenticated
  with check (user_id = auth.uid());

comment on table public.company_updates is 'Company-wide employee announcements (not job-scoped).';
comment on table public.company_update_reads is 'Optional per-user read receipts for company_updates.';
