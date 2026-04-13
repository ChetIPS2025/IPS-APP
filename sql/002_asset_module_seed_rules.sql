insert into public.asset_service_rules (asset_type, default_service_type, interval_days, interval_hours, interval_miles)
values
    ('Forklift', 'PM Service', 90, 250, 0),
    ('Truck', 'Oil Change', 180, 0, 5000),
    ('Welder', 'Inspection', 90, 0, 0),
    ('Generator', 'PM Service', 30, 100, 0),
    ('Compressor', 'PM Service', 90, 250, 0),
    ('Pump', 'Inspection', 180, 0, 0)
on conflict (asset_type) do nothing;
