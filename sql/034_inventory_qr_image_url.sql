-- Optional URL/path for generated inventory QR PNG (see app/services/qr_codes.py).
alter table public.inventory_items
    add column if not exists qr_code_image_url text;

comment on column public.inventory_items.qr_code_image_url is
    'Storage path or HTTPS URL for a pre-rendered QR PNG; optional when QR is rendered from qr_code_value.';
