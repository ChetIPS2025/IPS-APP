-- Enable RLS and grant authenticated users broad access (read + write) on core IPS tables.
-- Run in Supabase SQL editor after reviewing security posture for your environment.
--
-- Streamlit uses the anon/publishable key with a logged-in user JWT; PostgREST role is
-- typically `authenticated`. Service-role clients bypass RLS.
--
-- If a table already had RLS with stricter policies, review and merge manually.

-- --- jobs ---
alter table if exists public.jobs enable row level security;

drop policy if exists "Allow read access" on public.jobs;
create policy "Allow read access" on public.jobs for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.jobs;
create policy "Allow insert access" on public.jobs for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.jobs;
create policy "Allow update access" on public.jobs for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.jobs;
create policy "Allow delete access" on public.jobs for delete to authenticated using (true);

-- --- customers ---
alter table if exists public.customers enable row level security;

drop policy if exists "Allow read access" on public.customers;
create policy "Allow read access" on public.customers for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.customers;
create policy "Allow insert access" on public.customers for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.customers;
create policy "Allow update access" on public.customers for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.customers;
create policy "Allow delete access" on public.customers for delete to authenticated using (true);

-- --- customer_contacts (app table name; not "contacts") ---
alter table if exists public.customer_contacts enable row level security;

drop policy if exists "Allow read access" on public.customer_contacts;
create policy "Allow read access" on public.customer_contacts for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.customer_contacts;
create policy "Allow insert access" on public.customer_contacts for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.customer_contacts;
create policy "Allow update access" on public.customer_contacts for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.customer_contacts;
create policy "Allow delete access" on public.customer_contacts for delete to authenticated using (true);

-- --- estimates ---
alter table if exists public.estimates enable row level security;

drop policy if exists "Allow read access" on public.estimates;
create policy "Allow read access" on public.estimates for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.estimates;
create policy "Allow insert access" on public.estimates for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.estimates;
create policy "Allow update access" on public.estimates for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.estimates;
create policy "Allow delete access" on public.estimates for delete to authenticated using (true);

-- --- assets ---
alter table if exists public.assets enable row level security;

drop policy if exists "Allow read access" on public.assets;
create policy "Allow read access" on public.assets for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.assets;
create policy "Allow insert access" on public.assets for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.assets;
create policy "Allow update access" on public.assets for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.assets;
create policy "Allow delete access" on public.assets for delete to authenticated using (true);
