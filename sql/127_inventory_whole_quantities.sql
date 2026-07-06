-- Round existing inventory quantity fields to whole numbers.

update public.inventory_items
set
  quantity_on_hand = round(quantity_on_hand),
  reorder_point = round(reorder_point),
  quantity_checked_out = round(coalesce(quantity_checked_out, 0)),
  quantity_allocated = round(coalesce(quantity_allocated, 0))
where
  quantity_on_hand <> round(quantity_on_hand)
  or reorder_point <> round(reorder_point)
  or coalesce(quantity_checked_out, 0) <> round(coalesce(quantity_checked_out, 0))
  or coalesce(quantity_allocated, 0) <> round(coalesce(quantity_allocated, 0));

-- Round existing inventory transaction quantity fields to whole numbers.
-- Schema note: live inventory_transactions uses qty (signed), quantity, previous_quantity,
-- and new_quantity (027/073). quantity_delta exists only in legacy 004_inventory.sql.

update public.inventory_transactions
set
  qty = round(qty),
  quantity = round(quantity),
  previous_quantity = round(previous_quantity),
  new_quantity = round(new_quantity)
where
  qty <> round(qty)
  or coalesce(quantity, 0) <> round(coalesce(quantity, 0))
  or coalesce(previous_quantity, 0) <> round(coalesce(previous_quantity, 0))
  or coalesce(new_quantity, 0) <> round(coalesce(new_quantity, 0));
update public.pricing_guide_items
set
  default_reorder_point = round(default_reorder_point),
  default_reorder_quantity = round(default_reorder_quantity)
where
  default_reorder_point <> round(default_reorder_point)
  or default_reorder_quantity <> round(default_reorder_quantity);

update public.qr_scan_events
set quantity = round(quantity)
where quantity is not null and quantity <> round(quantity);
