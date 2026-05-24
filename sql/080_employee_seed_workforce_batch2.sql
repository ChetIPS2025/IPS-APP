-- Additional workforce employee seeds (upsert by employee_number when set).
-- Safe to re-run. Bryson Myers / Bryce Hebert (no IPS #) are seeded via app on Users page load.

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
        'Dylan C. Inzina',
        'General Laborer',
        'General Laborer',
        'IPS1350',
        'dylanroby05@gmail.com',
        '337-578-1995',
        'Active',
        true,
        true,
        'General Laborer',
        'Field Operations'
    ),
    (
        'Jamie J. Henson',
        'General Laborer',
        'General Laborer',
        'IPS5507',
        'jamiehenson@gmail.com',
        '225-450-5087',
        'Active',
        true,
        true,
        'General Laborer',
        'Field Operations'
    ),
    (
        'Dylan M. Eddy',
        'General Laborer',
        'General Laborer',
        'IPS4582',
        'dylaneddy683@yahoo.com',
        '337-789-9514',
        'Active',
        true,
        true,
        'General Laborer',
        'Field Operations'
    ),
    (
        'Amanda M. Robicheaux',
        'General Laborer',
        'General Laborer',
        'IPS5320',
        'amanda@industrialplantsolution.com',
        '985-519-5164',
        'Active',
        true,
        true,
        'General Laborer',
        'Field Operations'
    ),
    (
        'Brian A. LeBlanc',
        'General Laborer',
        'General Laborer',
        'IPS5772',
        'brianleblanc450@yahoo.com',
        '337-380-5687',
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
