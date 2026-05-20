-- =============================================================================
-- 008_documents.sql — Central documents hub
-- Depends on: 001_core.sql (profiles)
-- =============================================================================

create table if not exists public.documents_hub (
    id uuid primary key default gen_random_uuid(),
    file_name text not null,
    name text generated always as (file_name) stored,
    doc_type text not null default '',
    document_type text generated always as (doc_type) stored,
    linked_module text not null default '',
    linked_ref text not null default '',
    linked_record_id uuid,
    upload_date date not null default current_date,
    uploaded_by text not null default '',
    expiration_date date,
    is_restricted boolean not null default false,
    storage_path text not null default '',
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_documents_hub_module on public.documents_hub (linked_module);
create index if not exists idx_documents_hub_type on public.documents_hub (doc_type);
create index if not exists idx_documents_hub_linked_record on public.documents_hub (linked_record_id);
create index if not exists idx_documents_hub_upload_date on public.documents_hub (upload_date desc);

drop trigger if exists trg_documents_hub_updated_at on public.documents_hub;
create trigger trg_documents_hub_updated_at
    before update on public.documents_hub
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- RLS — non-restricted visible to authenticated; restricted admin-only
-- -----------------------------------------------------------------------------
alter table public.documents_hub enable row level security;

drop policy if exists documents_hub_select on public.documents_hub;
create policy documents_hub_select on public.documents_hub
    for select to authenticated
    using (not is_restricted or public.ips_is_admin());

drop policy if exists documents_hub_write on public.documents_hub;
create policy documents_hub_write on public.documents_hub
    for all to authenticated using (true) with check (true);

comment on table public.documents_hub is 'Cross-module document registry (IPS Documents page).';
