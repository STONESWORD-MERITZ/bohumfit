-- profiles 테이블에 role 컬럼 추가 (없으면)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE t.typname = 'user_role' AND n.nspname = 'public'
  ) THEN
    CREATE TYPE public.user_role AS ENUM ('customer', 'internal');
  END IF;
END $$;

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS role public.user_role NOT NULL DEFAULT 'customer';

UPDATE public.profiles
SET role = 'customer'
WHERE role::text = 'user';

ALTER TABLE public.profiles
  ALTER COLUMN role SET DEFAULT 'customer';

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'profiles'
      AND column_name = 'role'
      AND udt_name <> 'user_role'
  ) THEN
    ALTER TABLE public.profiles
      ALTER COLUMN role TYPE public.user_role
      USING CASE
        WHEN role::text = 'internal' THEN 'internal'::public.user_role
        ELSE 'customer'::public.user_role
      END;
  END IF;
END $$;

-- 구독 테이블
CREATE TABLE IF NOT EXISTS public.subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'inactive',   -- active | inactive | cancelled
  plan TEXT NOT NULL DEFAULT 'basic',        -- basic
  price_krw INTEGER NOT NULL DEFAULT 9900,
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  toss_customer_key TEXT,                    -- 토스페이먼츠 빌링키 연동용
  toss_billing_key TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id)
);

-- 사용량 로그 테이블
CREATE TABLE IF NOT EXISTS public.usage_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  used_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  period_start TIMESTAMPTZ NOT NULL,   -- 해당 월 구독 시작일
  period_end TIMESTAMPTZ NOT NULL      -- 해당 월 구독 종료일
);

-- RLS 활성화
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_logs ENABLE ROW LEVEL SECURITY;

-- subscriptions RLS: 본인만 조회 가능, 서비스롤만 변경 가능
CREATE POLICY "본인 구독 조회" ON public.subscriptions
  FOR SELECT USING (auth.uid() = user_id);

-- usage_logs RLS: 본인만 조회 가능, 서비스롤만 삽입 가능
CREATE POLICY "본인 사용량 조회" ON public.usage_logs
  FOR SELECT USING (auth.uid() = user_id);

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER subscriptions_updated_at
  BEFORE UPDATE ON public.subscriptions
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
