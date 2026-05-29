-- =============================================================================
-- Migration: Month/Year as single "month/year" period (e.g. 5/2026, 05/2026)
-- Run in Supabase SQL Editor AFTER the main schema.sql
-- =============================================================================

-- Generated display column from existing month + year (read-only)
ALTER TABLE public.salary_records
  ADD COLUMN IF NOT EXISTS pay_period TEXT
  GENERATED ALWAYS AS (month::text || '/' || year::text) STORED;

ALTER TABLE public.salary_slip_files
  ADD COLUMN IF NOT EXISTS pay_period TEXT
  GENERATED ALWAYS AS (month::text || '/' || year::text) STORED;

-- Optional: helper to parse "month/year" text when inserting from SQL
CREATE OR REPLACE FUNCTION public.parse_pay_period(period_text TEXT)
RETURNS TABLE (month SMALLINT, year INTEGER)
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
  parts TEXT[];
BEGIN
  parts := string_to_array(trim(period_text), '/');
  IF array_length(parts, 1) <> 2 THEN
    RAISE EXCEPTION 'Invalid period. Use month/year format, e.g. 5/2026';
  END IF;
  month := parts[1]::SMALLINT;
  year := parts[2]::INTEGER;
  IF month < 1 OR month > 12 THEN
    RAISE EXCEPTION 'Month must be between 1 and 12';
  END IF;
  IF year < 2000 THEN
    RAISE EXCEPTION 'Year must be 2000 or later';
  END IF;
  RETURN NEXT;
END;
$$;

-- Example insert using month/year string:
-- INSERT INTO public.salary_records (
--   employee_id, base_salary, hra, allowances, deductions, net_salary, month, year
-- )
-- SELECT
--   'EMP001', 50000, 15000, 5000, 2000, 68000, p.month, p.year
-- FROM public.parse_pay_period('5/2026') p;

CREATE INDEX IF NOT EXISTS salary_records_pay_period_idx ON public.salary_records (pay_period);
CREATE INDEX IF NOT EXISTS salary_slip_files_pay_period_idx ON public.salary_slip_files (pay_period);
