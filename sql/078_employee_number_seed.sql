-- Employee number + core workforce seed (upsert by employee_number).
-- Safe to re-run. Does not create auth users or passwords.

alter table if exists public.employees
    add column if not exists employee_number text;

alter table if exists public.employees
    add column if not exists position text not null default '';

alter table if exists public.employees
    add column if not exists hire_date date;

alter table if exists public.employees
    add column if not exists status text not null default 'Active';

alter table if exists public.employees
    add column if not exists is_employee boolean not null default true;

create unique index if not exists uq_employees_employee_number
    on public.employees (employee_number)
    where employee_number is not null and btrim(employee_number) <> '';

comment on column public.employees.employee_number is 'IPS workforce id (e.g. IPS0878); unique when set.';

-- Upsert core employees (match employee_number; preserve existing UUID id on update).
insert into public.employees (
    name,
    position,
    trade,
    hire_date,
    employee_number,
    email,
    phone,
    status,
    is_active,
    is_employee,
    role,
    department
)
values
    (
        'Chance Burgess',
        'Supervisor',
        'Supervisor',
        '2021-05-13'::date,
        'IPS0878',
        'chance.burgess@industrialplantsolution.com',
        '337-578-4324',
        'Active',
        true,
        true,
        'Supervisor',
        'Field Operations'
    ),
    (
        'Chet Breaux',
        'Supervisor',
        'Supervisor',
        '2020-07-26'::date,
        'IPS5197',
        'chet.breaux@industrialplantsolution.com',
        '337-577-3944',
        'Active',
        true,
        true,
        'Supervisor',
        'Field Operations'
    ),
    (
        'Titus Guilbeaux',
        'General Laborer',
        'General Laborer',
        '2023-05-15'::date,
        'IPS9417',
        'gkaylym@gmail.com',
        '337-241-2924',
        'Active',
        true,
        true,
        'General Laborer',
        'Field Operations'
    )
on conflict (employee_number) where employee_number is not null and btrim(employee_number) <> ''
do update set
    name = excluded.name,
    position = excluded.position,
    trade = excluded.trade,
    hire_date = excluded.hire_date,
    email = excluded.email,
    phone = excluded.phone,
    status = excluded.status,
    is_active = excluded.is_active,
    is_employee = excluded.is_employee,
    role = excluded.role,
    department = excluded.department,
    updated_at = now();
