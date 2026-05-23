-- Estimate costing: line-item tables, rollup columns, proposal terms.
-- Safe to re-run (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).

-- -----------------------------------------------------------------------------
-- estimates — costing rollups + default markups
-- -----------------------------------------------------------------------------
alter table if exists public.estimates
    add column if not exists description text not null default '';

alter table if exists public.estimates
    add column if not exists material_cost numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists labor_cost numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists equipment_cost numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists subcontractor_cost numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists other_cost numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists total_cost numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists total_markup numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists taxable_subtotal numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists tax_rate numeric(8, 4) not null default 0;

alter table if exists public.estimates
    add column if not exists tax_amount numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists customer_price numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists gross_profit numeric(14, 2) not null default 0;

alter table if exists public.estimates
    add column if not exists gross_margin_percent numeric(8, 4) not null default 0;

alter table if exists public.estimates
    add column if not exists default_material_markup_pct numeric(8, 4) not null default 0;

alter table if exists public.estimates
    add column if not exists default_labor_markup_pct numeric(8, 4) not null default 0;

alter table if exists public.estimates
    add column if not exists default_equipment_markup_pct numeric(8, 4) not null default 0;

alter table if exists public.estimates
    add column if not exists default_subcontractor_markup_pct numeric(8, 4) not null default 0;

alter table if exists public.estimates
    add column if not exists default_other_markup_pct numeric(8, 4) not null default 0;

alter table if exists public.estimates
    add column if not exists global_markup_pct numeric(8, 4) not null default 0;

alter table if exists public.estimates
    add column if not exists overhead_pct numeric(8, 4) not null default 0;

alter table if exists public.estimates
    add column if not exists profit_pct numeric(8, 4) not null default 0;

alter table if exists public.estimates
    add column if not exists proposal_show_line_items boolean not null default false;

alter table if exists public.estimates
    add column if not exists proposal_show_category_totals boolean not null default true;

alter table if exists public.estimates
    add column if not exists proposal_show_final_price_only boolean not null default false;

-- Backfill from legacy columns when new rollups are zero
update public.estimates
set material_cost = coalesce(nullif(material_cost, 0), material_total, 0),
    labor_cost = coalesce(nullif(labor_cost, 0), labor_total, 0),
    equipment_cost = coalesce(nullif(equipment_cost, 0), equipment_total, 0),
    total_cost = coalesce(nullif(total_cost, 0), subtotal, 0),
    customer_price = coalesce(nullif(customer_price, 0), total, grand_total, 0),
    tax_amount = coalesce(nullif(tax_amount, 0), tax, 0),
    total_markup = coalesce(nullif(total_markup, 0), markup, 0),
    description = coalesce(nullif(description, ''), notes, '')
where true;

-- -----------------------------------------------------------------------------
-- estimate_line_items — extended material costing (per-estimate lines)
-- -----------------------------------------------------------------------------
alter table if exists public.estimate_line_items
    add column if not exists sku text not null default '';

alter table if exists public.estimate_line_items
    add column if not exists vendor_id uuid;

alter table if exists public.estimate_line_items
    add column if not exists markup_percent numeric(8, 4) not null default 0;

alter table if exists public.estimate_line_items
    add column if not exists markup_amount numeric(14, 2) not null default 0;

alter table if exists public.estimate_line_items
    add column if not exists price_total numeric(14, 2) not null default 0;

alter table if exists public.estimate_line_items
    add column if not exists taxable boolean not null default true;

update public.estimate_line_items
set sku = coalesce(nullif(sku, ''), nullif(item_number, ''), '')
where coalesce(sku, '') = '';

update public.estimate_line_items
set price_total = coalesce(nullif(price_total, 0), total_cost + markup_amount, total_cost, 0)
where coalesce(price_total, 0) = 0;

-- -----------------------------------------------------------------------------
-- estimate_labor_lines — ST/OT/DT costing
-- -----------------------------------------------------------------------------
alter table if exists public.estimate_labor_lines
    add column if not exists role_name text not null default '';

alter table if exists public.estimate_labor_lines
    add column if not exists employee_id uuid;

alter table if exists public.estimate_labor_lines
    add column if not exists st_hours numeric not null default 0;

alter table if exists public.estimate_labor_lines
    add column if not exists ot_hours numeric not null default 0;

alter table if exists public.estimate_labor_lines
    add column if not exists dt_hours numeric not null default 0;

alter table if exists public.estimate_labor_lines
    add column if not exists st_rate numeric not null default 0;

alter table if exists public.estimate_labor_lines
    add column if not exists ot_rate numeric not null default 0;

alter table if exists public.estimate_labor_lines
    add column if not exists dt_rate numeric not null default 0;

alter table if exists public.estimate_labor_lines
    add column if not exists cost_total numeric not null default 0;

alter table if exists public.estimate_labor_lines
    add column if not exists markup_percent numeric(8, 4) not null default 0;

alter table if exists public.estimate_labor_lines
    add column if not exists markup_amount numeric(14, 2) not null default 0;

alter table if exists public.estimate_labor_lines
    add column if not exists price_total numeric(14, 2) not null default 0;

alter table if exists public.estimate_labor_lines
    add column if not exists notes text not null default '';

-- Backfill legacy hours/rate/total
update public.estimate_labor_lines
set st_hours = coalesce(nullif(st_hours, 0), hours, 0),
    st_rate = coalesce(nullif(st_rate, 0), rate, 0),
    cost_total = coalesce(nullif(cost_total, 0), total, 0),
    role_name = coalesce(nullif(role_name, ''), nullif(description, ''), labor_type, '')
where true;

-- -----------------------------------------------------------------------------
-- estimate_equipment
-- -----------------------------------------------------------------------------
create table if not exists public.estimate_equipment (
    id uuid primary key default gen_random_uuid(),
    estimate_id uuid not null references public.estimates (id) on delete cascade,
    asset_id uuid,
    equipment_name text not null default '',
    equipment_type text not null default '',
    quantity numeric not null default 1,
    duration numeric not null default 0,
    duration_unit text not null default 'Hours',
    cost_rate numeric not null default 0,
    cost_total numeric not null default 0,
    markup_percent numeric(8, 4) not null default 0,
    markup_amount numeric(14, 2) not null default 0,
    price_total numeric(14, 2) not null default 0,
    notes text not null default '',
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_estimate_equipment_estimate
    on public.estimate_equipment (estimate_id, sort_order);

-- -----------------------------------------------------------------------------
-- estimate_subcontractors
-- -----------------------------------------------------------------------------
create table if not exists public.estimate_subcontractors (
    id uuid primary key default gen_random_uuid(),
    estimate_id uuid not null references public.estimates (id) on delete cascade,
    vendor_id uuid,
    subcontractor_name text not null default '',
    description text not null default '',
    cost_total numeric not null default 0,
    markup_percent numeric(8, 4) not null default 0,
    markup_amount numeric(14, 2) not null default 0,
    price_total numeric(14, 2) not null default 0,
    notes text not null default '',
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_estimate_subcontractors_estimate
    on public.estimate_subcontractors (estimate_id, sort_order);

-- -----------------------------------------------------------------------------
-- estimate_other_costs
-- -----------------------------------------------------------------------------
create table if not exists public.estimate_other_costs (
    id uuid primary key default gen_random_uuid(),
    estimate_id uuid not null references public.estimates (id) on delete cascade,
    description text not null default '',
    category text not null default '',
    cost_total numeric not null default 0,
    markup_percent numeric(8, 4) not null default 0,
    markup_amount numeric(14, 2) not null default 0,
    price_total numeric(14, 2) not null default 0,
    taxable boolean not null default false,
    notes text not null default '',
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_estimate_other_costs_estimate
    on public.estimate_other_costs (estimate_id, sort_order);

-- -----------------------------------------------------------------------------
-- estimate_terms — reusable proposal terms
-- -----------------------------------------------------------------------------
create table if not exists public.estimate_terms (
    id uuid primary key default gen_random_uuid(),
    name text not null default '',
    terms_text text not null default '',
    is_default boolean not null default false,
    created_at timestamptz not null default now()
);

-- Default IPS terms
insert into public.estimate_terms (name, terms_text, is_default)
select
    'Standard IPS Proposal Terms',
    'Payment terms: Net 30 from invoice date. Proposal valid through expiration date shown above. '
    || 'Work performed per IPS safety standards and applicable codes. Change orders require written approval. '
    || 'Acceptance signature below authorizes IPS to proceed with scope described.',
    true
where not exists (
    select 1 from public.estimate_terms where is_default = true
);

-- -----------------------------------------------------------------------------
-- RLS
-- -----------------------------------------------------------------------------
alter table if exists public.estimate_equipment enable row level security;
alter table if exists public.estimate_subcontractors enable row level security;
alter table if exists public.estimate_other_costs enable row level security;
alter table if exists public.estimate_terms enable row level security;

drop policy if exists estimate_equipment_all on public.estimate_equipment;
create policy estimate_equipment_all on public.estimate_equipment for all to authenticated using (true) with check (true);

drop policy if exists estimate_subcontractors_all on public.estimate_subcontractors;
create policy estimate_subcontractors_all on public.estimate_subcontractors for all to authenticated using (true) with check (true);

drop policy if exists estimate_other_costs_all on public.estimate_other_costs;
create policy estimate_other_costs_all on public.estimate_other_costs for all to authenticated using (true) with check (true);

drop policy if exists estimate_terms_all on public.estimate_terms;
create policy estimate_terms_all on public.estimate_terms for all to authenticated using (true) with check (true);
