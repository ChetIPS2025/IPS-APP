-- Audit: who scanned / issued inventory (mobile QR flow). Run after sql/027_inventory_qr_and_transactions.sql.
-- scanned_by_user_id stores profile id or auth user id as text (no FK — avoids coupling to auth schema changes).

alter table public.inventory_transactions
    add column if not exists scanned_by_user_id text;

alter table public.inventory_transactions
    add column if not exists scanned_by_name text;

alter table public.inventory_transactions
    add column if not exists device_label text;

comment on column public.inventory_transactions.scanned_by_user_id is 'Profile or auth user id when known; null if manual-only issue.';
comment on column public.inventory_transactions.scanned_by_name is 'Display name at scan time (full_name, email, or manual entry).';
comment on column public.inventory_transactions.device_label is 'Optional shared device / cart label from scan UI.';
