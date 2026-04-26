-- Optional item photo for inventory list / scan / dashboard (storage path or HTTPS URL).
alter table public.inventory_items
    add column if not exists image_url text;

comment on column public.inventory_items.image_url is
    'Thumbnail path in storage (e.g. inventory/items/<id>.jpg) or full HTTPS URL.';
