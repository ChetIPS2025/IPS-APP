-- Optional model / serial metadata on quantity hand tools (import + display).

alter table if exists public.small_hand_tools
    add column if not exists model_number text not null default '',
    add column if not exists serial_number text not null default '';

comment on column public.small_hand_tools.model_number is
    'Manufacturer model or part number (optional; quantity tools are not serialized-tracked).';
comment on column public.small_hand_tools.serial_number is
    'Optional tag or lot serial when a hand tool has a physical serial (rare).';
