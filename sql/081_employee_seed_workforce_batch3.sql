-- Workforce employee seeds batch 3 (upsert by employee_number).
-- Safe to re-run.

insert into public.employees (
    name,
    position,
    trade,
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
        'Jenny L. Loveless',
        'General Laborer',
        'General Laborer',
        'IPS3725',
        'jenny-loveless@yahoo.com',
        '337-258-7999',
        'Active',
        true,
        true,
        'General Laborer',
        'Field Operations'
    ),
    (
        'Talyon Charles Robicheaux',
        'General Laborer',
        'General Laborer',
        'IPS2193',
        'talyonrobicheaux@yahoo.com',
        '337-578-0182',
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
    email = excluded.email,
    phone = excluded.phone,
    status = excluded.status,
    is_active = excluded.is_active,
    is_employee = excluded.is_employee,
    role = excluded.role,
    department = excluded.department,
    updated_at = now();
