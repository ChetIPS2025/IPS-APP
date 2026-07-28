-- Speed up Pricing Guide catalog ordering and search by description.
create index if not exists idx_pricing_guide_items_description
    on public.pricing_guide_items (description);
