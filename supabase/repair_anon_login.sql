-- ═══════════════════════════════════════════════════════════
-- 익명 로그인 실패 복구
--   증상: 앱 시작 시 "저장소 연결에 실패했어요"
--   원인: 가입 트리거(handle_new_user)가 profiles 삽입 중 DB 에러로 실패
--         → "Database error creating anonymous user"
-- 사용법: Supabase Dashboard > SQL Editor 에 전체 붙여넣기 → Run
-- ═══════════════════════════════════════════════════════════

-- 1) profiles.email 을 nullable 로 (익명 유저는 email 이 없음)
alter table public.profiles alter column email drop not null;

-- 2) nick 기본값 보장
alter table public.profiles alter column nick set default '사용자';

-- 3) 가입 트리거를 예외 안전하게 교체
--    (profiles 생성이 실패해도 가입=익명 로그인은 막지 않는다)
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
