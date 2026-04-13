-- Optional columns used by Asset Manager / Asset Photo Autofill (align with app payloads).
alter table public.assets
    add column if not exists inspection_due_date date null,
    add column if not exists maintenance_due_date date null;
