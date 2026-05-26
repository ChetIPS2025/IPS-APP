-- Pricing guide stock policy: mandatory vs optional inventory tracking.
-- Run after sql/090_catalog_relationships.sql.

alter table public.pricing_guide_items
    add column if not exists stock_policy text not null default 'none',
    add column if not exists default_reorder_point numeric not null default 0,
    add column if not exists default_reorder_quantity numeric not null default 0;

alter table public.pricing_guide_items
    drop constraint if exists pricing_guide_items_stock_policy_check;

alter table public.pricing_guide_items
    add constraint pricing_guide_items_stock_policy_check
    check (stock_policy in ('none', 'optional', 'mandatory'));

comment on column public.pricing_guide_items.stock_policy is
    'none = not stocked; optional = stock extras only; mandatory = always track and reorder when low.';
comment on column public.pricing_guide_items.default_reorder_point is
    'Default reorder threshold copied to linked inventory_items.reorder_point.';
comment on column public.pricing_guide_items.default_reorder_quantity is
    'Suggested reorder qty (reserved for future PO workflow).';

update public.pricing_guide_items
set stock_policy = 'mandatory'
where coalesce(linked_inventory_id, inventory_item_id) is not null
  and stock_policy = 'none';
