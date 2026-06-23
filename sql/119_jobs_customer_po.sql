-- Customer PO fields on jobs (po_number added in 088).
BEGIN;

ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS po_date date,
    ADD COLUMN IF NOT EXISTS po_amount numeric(14, 2);

COMMENT ON COLUMN public.jobs.po_number IS 'Customer purchase order number.';
COMMENT ON COLUMN public.jobs.po_date IS 'Customer PO date.';
COMMENT ON COLUMN public.jobs.po_amount IS 'Customer PO amount ($).';

COMMIT;
