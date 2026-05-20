-- =============================================================================
-- 007_employees.sql — Employees / HR extensions
-- Depends on: 001_core.sql (employees, profiles)
-- =============================================================================

-- Extra columns on employees (safe if 001 already defined them)
alter table public.employees add column if not exists email text;
alter table public.employees add column if not exists phone text;
alter table public.employees add column if not exists username text;
alter table public.employees add column if not exists position text not null default '';
alter table public.employees add column if not exists crew text not null default '';
alter table public.employees add column if not exists pay_type text not null default '';
alter table public.employees add column if not exists hire_date date;
alter table public.employees add column if not exists status text not null default 'Active';
alter table public.employees add column if not exists supervisor_id uuid references public.employees (id) on delete set null;
alter table public.employees add column if not exists department_id uuid references public.departments (id) on delete set null;

-- -----------------------------------------------------------------------------
-- employee_certifications
-- -----------------------------------------------------------------------------
create table if not exists public.employee_certifications (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    cert_type text not null,
    cert_number text not null default '',
    issuer text not null default '',
    issuing_organization text generated always as (issuer) stored,
    issue_date date,
    expiration_date date,
    status text not null default 'Active',
    attachment_path text not null default '',
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint employee_certifications_status_check
        check (status in ('Active', 'Expiring Soon', 'Expired', 'Inactive'))
);

create index if not exists idx_employee_certifications_employee
    on public.employee_certifications (employee_id);
create index if not exists idx_employee_certifications_exp
    on public.employee_certifications (expiration_date);
create index if not exists idx_employee_certifications_type
    on public.employee_certifications (cert_type);

drop trigger if exists trg_employee_certifications_updated_at on public.employee_certifications;
create trigger trg_employee_certifications_updated_at
    before update on public.employee_certifications
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- employee_documents (HR — restricted docs admin-only in RLS)
-- -----------------------------------------------------------------------------
create table if not exists public.employee_documents (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    doc_type text not null,
    document_type text generated always as (doc_type) stored,
    file_name text not null,
    upload_date date not null default current_date,
    uploaded_by text not null default '',
    expiration_date date,
    is_restricted boolean not null default false,
    storage_path text not null default '',
    notes text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists idx_employee_documents_employee
    on public.employee_documents (employee_id);
create index if not exists idx_employee_documents_type
    on public.employee_documents (doc_type);

-- -----------------------------------------------------------------------------
-- employee_activity_log
-- -----------------------------------------------------------------------------
create table if not exists public.employee_activity_log (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    activity_type text not null default 'note',
    description text not null default '',
    created_by uuid references public.profiles (id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists idx_employee_activity_employee
    on public.employee_activity_log (employee_id, created_at desc);

-- -----------------------------------------------------------------------------
-- RLS
-- -----------------------------------------------------------------------------
alter table public.employee_certifications enable row level security;
alter table public.employee_documents enable row level security;
alter table public.employee_activity_log enable row level security;

drop policy if exists employee_certifications_select on public.employee_certifications;
create policy employee_certifications_select on public.employee_certifications
    for select to authenticated
    using (
        public.ips_is_admin()
        or public.ips_current_role() in ('Supervisor', 'Project Manager', 'Admin', 'admin')
        or employee_id = (select employee_id from public.profiles where id = auth.uid() limit 1)
    );

drop policy if exists employee_certifications_write on public.employee_certifications;
create policy employee_certifications_write on public.employee_certifications
    for all to authenticated
    using (public.ips_is_admin() or public.ips_current_role() in ('Supervisor', 'Project Manager'))
    with check (public.ips_is_admin() or public.ips_current_role() in ('Supervisor', 'Project Manager'));

drop policy if exists employee_documents_select on public.employee_documents;
create policy employee_documents_select on public.employee_documents
    for select to authenticated
    using (
        (
            not is_restricted
            and (
                public.ips_is_admin()
                or public.ips_current_role() in ('Supervisor', 'Project Manager')
                or employee_id = (select employee_id from public.profiles where id = auth.uid() limit 1)
            )
        )
        or public.ips_is_admin()
    );

drop policy if exists employee_documents_write on public.employee_documents;
create policy employee_documents_write on public.employee_documents
    for all to authenticated
    using (public.ips_is_admin())
    with check (public.ips_is_admin());

drop policy if exists employee_activity_log_all on public.employee_activity_log;
create policy employee_activity_log_all on public.employee_activity_log
    for all to authenticated using (true) with check (true);

comment on table public.employee_certifications is 'TWIC, OSHA, site certs, etc.';
comment on table public.employee_documents is 'Per-employee HR files; is_restricted requires Admin to read.';
