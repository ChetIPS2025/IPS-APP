-- Extend employee_certifications for compliance statuses and attachment storage.

alter table public.employee_certifications
    add column if not exists attachment_path text not null default '';

alter table public.employee_certifications
    drop constraint if exists employee_certifications_status_check;

alter table public.employee_certifications
    add constraint employee_certifications_status_check
    check (status in ('Active', 'Expiring Soon', 'Expired', 'Missing', 'Not Required', 'Inactive'));
