-- Private Storage bucket for employee certification attachments (PDF/images).
-- App uploads via service role and serves signed URLs from certification_attachments_service.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'certification-documents',
    'certification-documents',
    false,
    52428800,
    array['image/png', 'image/jpeg', 'image/webp', 'application/pdf']::text[]
)
on conflict (id) do nothing;

drop policy if exists certification_docs_select_auth on storage.objects;
create policy certification_docs_select_auth
    on storage.objects
    for select
    to authenticated
    using (bucket_id = 'certification-documents');

drop policy if exists certification_docs_insert_role_based on storage.objects;
create policy certification_docs_insert_role_based
    on storage.objects
    for insert
    to authenticated
    with check (
        bucket_id = 'certification-documents'
        and exists (
            select 1
            from public.profiles p
            where p.id = auth.uid()
              and coalesce(p.is_active, true) = true
              and p.role = any (array['admin', 'supervisor', 'project manager']::text[])
        )
    );

drop policy if exists certification_docs_update_role_based on storage.objects;
create policy certification_docs_update_role_based
    on storage.objects
    for update
    to authenticated
    using (
        bucket_id = 'certification-documents'
        and exists (
            select 1
            from public.profiles p
            where p.id = auth.uid()
              and coalesce(p.is_active, true) = true
              and p.role = any (array['admin', 'supervisor', 'project manager']::text[])
        )
    )
    with check (
        bucket_id = 'certification-documents'
        and exists (
            select 1
            from public.profiles p
            where p.id = auth.uid()
              and coalesce(p.is_active, true) = true
              and p.role = any (array['admin', 'supervisor', 'project manager']::text[])
        )
    );

drop policy if exists certification_docs_delete_admin_only on storage.objects;
create policy certification_docs_delete_admin_only
    on storage.objects
    for delete
    to authenticated
    using (
        bucket_id = 'certification-documents'
        and exists (
            select 1
            from public.profiles p
            where p.id = auth.uid()
              and coalesce(p.is_active, true) = true
              and p.role = 'admin'
        )
    );
