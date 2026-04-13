-- Optional metadata for asset_documents (manuals, PDFs, Office files).
-- Run in Supabase SQL editor if these columns are missing.

alter table public.asset_documents
  add column if not exists content_type text default '';

alter table public.asset_documents
  add column if not exists original_filename text default '';

alter table public.asset_documents
  add column if not exists file_kind text default 'document';

comment on column public.asset_documents.content_type is 'MIME type stored with the file (e.g. application/pdf).';
comment on column public.asset_documents.original_filename is 'Original upload filename (same as file_name when not renamed).';
comment on column public.asset_documents.file_kind is 'document | manual | other — distinguishes from photos in asset_photos.';
