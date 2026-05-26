-- Per-day approval on employee timekeeping day rows.

alter table public.employee_timekeeping_days
    add column if not exists status text not null default 'Draft';

alter table public.employee_timekeeping_days
    add column if not exists approved_by uuid references public.profiles (id) on delete set null;

alter table public.employee_timekeeping_days
    add column if not exists approved_at timestamptz;

alter table public.employee_timekeeping_days
    drop constraint if exists employee_timekeeping_days_status_check;

alter table public.employee_timekeeping_days
    add constraint employee_timekeeping_days_status_check
        check (status in ('Draft', 'Pending', 'Approved', 'Rejected'));

comment on column public.employee_timekeeping_days.status is 'Daily timecard approval status.';
