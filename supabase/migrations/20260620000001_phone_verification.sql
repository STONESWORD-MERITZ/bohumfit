-- BOHUMFIT-074: 휴대폰 본인인증(1인 1계정·어뷰징 방지) — profiles 컬럼 추가.
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS phone TEXT,
  ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN NOT NULL DEFAULT false;
