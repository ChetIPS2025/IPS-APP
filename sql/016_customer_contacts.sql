-- Multiple contacts per customer (company). Run in Supabase after prior migrations.

-- ---------------------------------------------------------------------------
-- 1) Contacts table
-- ---------------------------------------------------------------------------
create table if not exists public.customer_contacts (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid not null references public.customers (id) on delete cascade,
    contact_name text not null default '',
    role text not null default '',
    email text not null default '',
    phone text not null default '',
    is_primary boolean not null default false,
    is_active boolean not null default true,
    notes text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists idx_customer_contacts_customer_id
    on public.customer_contacts (customer_id);

create index if not exists idx_customer_contacts_customer_id_active
    on public.customer_contacts (customer_id, is_active);

comment on table public.customer_contacts is 'People/contacts for a customer company (customers row).';

-- ---------------------------------------------------------------------------
-- 2) Optional FK on estimates / jobs (nullable)
-- ---------------------------------------------------------------------------
alter table public.estimates
    add column if not exists customer_contact_id uuid;

alter table public.jobs
    add column if not exists customer_contact_id uuid;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'estimates_customer_contact_id_fkey'
    ) then
        alter table public.estimates
            add constraint estimates_customer_contact_id_fkey
            foreign key (customer_contact_id) references public.customer_contacts (id)
            on delete set null;
    end if;
exception
    when undefined_table then
        null;
end $$;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'jobs_customer_contact_id_fkey'
    ) then
        alter table public.jobs
            add constraint jobs_customer_contact_id_fkey
            foreign key (customer_contact_id) references public.customer_contacts (id)
            on delete set null;
    end if;
exception
    when undefined_table then
        null;
end $$;

-- ---------------------------------------------------------------------------
-- 3) Migrate legacy single-contact columns on customers (if present)
-- ---------------------------------------------------------------------------
do $$
begin
    if exists (
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'customers'
          and column_name = 'contact_name'
    ) then
        insert into public.customer_contacts (
            customer_id,
            contact_name,
            role,
            email,
            phone,
            is_primary,
            is_active,
            notes
        )
        select
            c.id,
            coalesce(nullif(btrim(c.contact_name), ''), 'Primary contact'),
            '',
            coalesce(c.email, ''),
            coalesce(c.phone, ''),
            true,
            true,
            ''
        from public.customers c
        where not exists (
            select 1 from public.customer_contacts cc where cc.customer_id = c.id
        )
          and (
              nullif(btrim(c.contact_name), '') is not null
              or nullif(btrim(c.email), '') is not null
              or nullif(btrim(c.phone), '') is not null
          );

        alter table public.customers drop column if exists contact_name;
        alter table public.customers drop column if exists email;
        alter table public.customers drop column if exists phone;
    end if;
end $$;
