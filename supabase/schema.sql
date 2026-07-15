-- ═══════════════════════════════════════════════════════════
-- 알약 pill-app — Supabase schema
-- Supabase Dashboard > SQL Editor 에 전체 붙여넣기 → Run
-- ═══════════════════════════════════════════════════════════

-- ── profiles ──────────────────────────────────────────────
create table if not exists public.profiles (
  id uuid primary key references auth.users on delete cascade,
  email text unique,
  nick text not null default '사용자',
  updated_at timestamptz not null default now()
);
alter table public.profiles enable row level security;

create policy "profiles: read own"
  on public.profiles for select using (auth.uid() = id);
create policy "profiles: update own"
  on public.profiles for update using (auth.uid() = id);
create policy "profiles: insert own"
  on public.profiles for insert with check (auth.uid() = id);

-- 회원가입 시 프로필 자동 생성 (익명 로그인은 email/메타데이터가 없어 '게스트'로)
-- 프로필 생성이 어떤 이유로 실패하더라도 가입(익명 로그인 포함) 자체는 막지 않도록
-- insert 를 예외 처리로 감싼다. (실패 시 profiles 행만 없고 로그인은 정상)
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  begin
    insert into public.profiles (id, email, nick)
    values (
      new.id, new.email,
      coalesce(
        nullif(new.raw_user_meta_data->>'nick', ''),
        nullif(new.raw_user_meta_data->>'full_name', ''),
        nullif(new.raw_user_meta_data->>'name', ''),
        nullif(split_part(coalesce(new.email, ''), '@', 1), ''),
        '게스트'
      )
    )
    on conflict (id) do nothing;
  exception when others then
    null;  -- 프로필 생성 실패해도 가입은 진행
  end;
  return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ── medications (내 약) ───────────────────────────────────
create table if not exists public.medications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users on delete cascade,
  name text not null,
  dosage text not null default '',
  times text[] not null default '{}',        -- morning | noon | evening | night
  start_date date not null default current_date,
  end_date date,                             -- null = 계속 복용
  color text not null default 'blue',
  memo text not null default '',
  created_at timestamptz not null default now()
);
alter table public.medications enable row level security;

create policy "medications: own"
  on public.medications for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create index if not exists medications_user_idx on public.medications (user_id);

-- ── medication_logs (복용 기록) ───────────────────────────
create table if not exists public.medication_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users on delete cascade,
  medication_id uuid not null references public.medications on delete cascade,
  date date not null,
  time_slot text not null,                   -- morning | noon | evening | night
  taken_at timestamptz not null default now(),
  unique (medication_id, date, time_slot)
);
alter table public.medication_logs enable row level security;

create policy "medication_logs: own"
  on public.medication_logs for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create index if not exists medication_logs_user_date_idx
  on public.medication_logs (user_id, date);
