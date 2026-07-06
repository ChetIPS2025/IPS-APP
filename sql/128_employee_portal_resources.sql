-- Employee Portal: extend toolbox links for role visibility and admin metadata.
-- Run after 014_employee_toolbox_resource_files.sql.

BEGIN;

ALTER TABLE public.employee_toolbox_links
    ADD COLUMN IF NOT EXISTS visible_to_roles text NOT NULL DEFAULT 'employee,supervisor,admin,project manager',
    ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

COMMENT ON COLUMN public.employee_toolbox_links.visible_to_roles IS
    'Comma-separated roles that may see this resource (employee, supervisor, admin, project manager).';
COMMENT ON COLUMN public.employee_toolbox_links.updated_at IS
    'Last time an administrator changed this resource.';

COMMIT;
