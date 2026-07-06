-- Allow damage reports in rental equipment inspections.

alter table if exists public.rental_equipment_inspections
  drop constraint if exists rental_equipment_inspections_type_check;

alter table if exists public.rental_equipment_inspections
  add constraint rental_equipment_inspections_type_check
  check (inspection_type in ('checkout', 'daily', 'return', 'damage'));
