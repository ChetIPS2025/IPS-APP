-- Employee Toolbox: curated links to documents and resources (run in Supabase SQL after prior migrations).

create table if not exists public.employee_toolbox_links (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    url text not null,
    description text not null default '',
    category text not null default '',
    is_active boolean not null default true,
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_employee_toolbox_links_active_sort
    on public.employee_toolbox_links (is_active, sort_order);

create index if not exists idx_employee_toolbox_links_created
    on public.employee_toolbox_links (created_at desc);

comment on table public.employee_toolbox_links is 'IPS Employee Toolbox: shared document/resource links for staff.';
comment on column public.employee_toolbox_links.sort_order is 'Lower numbers appear first; default ordering with created_at as tie-breaker in app.';
