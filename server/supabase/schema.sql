-- =============================================================================
-- Toyota Payroll + Salary Slip Storage — run in Supabase SQL Editor
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1) Auth profiles (admin dashboard login)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
    CREATE TYPE public.user_role AS ENUM ('admin', 'staff');
  END IF;
END$$;

CREATE TABLE IF NOT EXISTS public.admin_profiles (
  id          UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
  email       TEXT NOT NULL UNIQUE,
  full_name   TEXT,
  role        public.user_role NOT NULL DEFAULT 'staff',
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS admin_profiles_set_updated_at ON public.admin_profiles;
CREATE TRIGGER admin_profiles_set_updated_at
  BEFORE UPDATE ON public.admin_profiles
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.admin_profiles (id, email, full_name, is_active)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', SPLIT_PART(NEW.email, '@', 1)),
    TRUE
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();

-- -----------------------------------------------------------------------------
-- 2) Employees & salary records (mirror of payroll data; optional sync from Django)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.employees (
  employee_id   TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  email         TEXT NOT NULL,
  designation   TEXT DEFAULT '',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.salary_records (
  id            BIGSERIAL PRIMARY KEY,
  employee_id   TEXT NOT NULL REFERENCES public.employees (employee_id) ON DELETE CASCADE,
  base_salary   NUMERIC(12, 2) NOT NULL DEFAULT 0,
  hra           NUMERIC(12, 2) NOT NULL DEFAULT 0,
  allowances    NUMERIC(12, 2) NOT NULL DEFAULT 0,
  deductions    NUMERIC(12, 2) NOT NULL DEFAULT 0,
  net_salary    NUMERIC(12, 2) NOT NULL DEFAULT 0,
  month         SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
  year          INTEGER NOT NULL CHECK (year >= 2000),
  pay_period    TEXT GENERATED ALWAYS AS (month::text || '/' || year::text) STORED,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (employee_id, month, year)
);

CREATE INDEX IF NOT EXISTS salary_records_period_idx ON public.salary_records (year, month);
CREATE INDEX IF NOT EXISTS salary_records_pay_period_idx ON public.salary_records (pay_period);

-- -----------------------------------------------------------------------------
-- 3) Salary slip file registry (links PDF in Storage bucket to each employee)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.salary_slip_files (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id     TEXT NOT NULL REFERENCES public.employees (employee_id) ON DELETE CASCADE,
  employee_name   TEXT NOT NULL,
  month           SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
  year            INTEGER NOT NULL CHECK (year >= 2000),
  pay_period      TEXT GENERATED ALWAYS AS (month::text || '/' || year::text) STORED,
  file_name       TEXT NOT NULL,
  storage_path    TEXT NOT NULL,
  bucket_id       TEXT NOT NULL DEFAULT 'salary-slips',
  net_salary      NUMERIC(12, 2),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (employee_id, month, year)
);

CREATE INDEX IF NOT EXISTS salary_slip_files_period_idx ON public.salary_slip_files (year, month);
CREATE INDEX IF NOT EXISTS salary_slip_files_employee_idx ON public.salary_slip_files (employee_id);

-- -----------------------------------------------------------------------------
-- 4) Storage bucket for PDF salary slips
-- Path pattern: {year}/{month}/{employee_id}_{employee_name}.pdf
-- Example: 2026/05/EMP001_Raj_Kumar.pdf
-- -----------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'salary-slips',
  'salary-slips',
  FALSE,
  10485760,
  ARRAY['application/pdf']::text[]
)
ON CONFLICT (id) DO UPDATE SET
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- -----------------------------------------------------------------------------
-- 5) Row Level Security
-- -----------------------------------------------------------------------------
ALTER TABLE public.admin_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.salary_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.salary_slip_files ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.is_admin_user()
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.admin_profiles
    WHERE id = auth.uid() AND is_active = TRUE
  );
$$;

-- admin_profiles
DROP POLICY IF EXISTS "read own profile" ON public.admin_profiles;
CREATE POLICY "read own profile" ON public.admin_profiles
  FOR SELECT TO authenticated USING (auth.uid() = id);

DROP POLICY IF EXISTS "staff read all profiles" ON public.admin_profiles;
CREATE POLICY "staff read all profiles" ON public.admin_profiles
  FOR SELECT TO authenticated USING (public.is_admin_user());

-- employees & salaries & slip registry (authenticated admins)
DROP POLICY IF EXISTS "admins read employees" ON public.employees;
CREATE POLICY "admins read employees" ON public.employees
  FOR SELECT TO authenticated USING (public.is_admin_user());

DROP POLICY IF EXISTS "admins read salary_records" ON public.salary_records;
CREATE POLICY "admins read salary_records" ON public.salary_records
  FOR SELECT TO authenticated USING (public.is_admin_user());

DROP POLICY IF EXISTS "admins read salary_slip_files" ON public.salary_slip_files;
CREATE POLICY "admins read salary_slip_files" ON public.salary_slip_files
  FOR SELECT TO authenticated USING (public.is_admin_user());

-- Storage: admins can read/download slips
DROP POLICY IF EXISTS "admins read salary slip objects" ON storage.objects;
CREATE POLICY "admins read salary slip objects" ON storage.objects
  FOR SELECT TO authenticated
  USING (bucket_id = 'salary-slips' AND public.is_admin_user());

GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON public.employees, public.salary_records, public.salary_slip_files TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_admin_user() TO authenticated;
