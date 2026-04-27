-- Keep public.profiles linked to auth.users forever (profiles.id == auth.users.id)
-- Safe, link-aware trigger: normalizes email, links existing email profile to NEW.id, inserts if missing.

-- 1) Unique email protection (case-insensitive)
CREATE UNIQUE INDEX IF NOT EXISTS profiles_email_lower_unique
ON public.profiles (lower(email))
WHERE email IS NOT NULL;

-- 2) Trigger function (SECURITY DEFINER) to upsert/link profile on new auth user
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_email text;
  v_role text;
BEGIN
  v_email := lower(coalesce(NEW.email, ''));
  IF v_email = '' THEN
    RETURN NEW;
  END IF;

  -- Normalize and constrain role to allowed values; default to admin when unknown.
  v_role := lower(coalesce(NEW.raw_user_meta_data->>'role', ''));
  IF v_role IN ('pm', 'estimator') THEN
    v_role := 'manager';
  END IF;
  IF v_role NOT IN ('admin', 'manager', 'employee', 'viewer') THEN
    v_role := 'admin';
  END IF;

  -- If a profile exists for this email but has the wrong id, link it to this auth user id.
  -- Guard against colliding with an existing row already at NEW.id.
  UPDATE public.profiles
  SET
    id = NEW.id,
    email = v_email,
    is_active = true,
    must_reset_password = true
  WHERE lower(email) = v_email
    AND id <> NEW.id
    AND NOT EXISTS (
      SELECT 1 FROM public.profiles p2 WHERE p2.id = NEW.id
    );

  -- Insert profile if missing (by id or email).
  INSERT INTO public.profiles (
    id,
    email,
    full_name,
    role,
    is_active,
    must_reset_password,
    created_at
  )
  SELECT
    NEW.id,
    v_email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
    v_role,
    true,
    true,
    now()
  WHERE NOT EXISTS (
    SELECT 1
    FROM public.profiles
    WHERE id = NEW.id
       OR lower(email) = v_email
  );

  -- If profile exists by id but email differs only by case/spacing, normalize it.
  UPDATE public.profiles
  SET email = v_email
  WHERE id = NEW.id
    AND (email IS NULL OR lower(email) <> v_email);

  RETURN NEW;
END;
$$;

-- 3) Replace trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION public.handle_new_user();

