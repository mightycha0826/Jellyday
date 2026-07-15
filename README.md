# Jellyday

복약 관리 모바일 웹앱. 매일의 복약 체크, 캘린더 기록, 알약 촬영·식별(목업)을 제공합니다.
토스 디자인 언어를 참고한 화이트/블루 UI.

## 기술 스택

- Svelte 5 (runes) + SvelteKit 2 + TypeScript — SPA 모드 (`ssr = false`)
- Supabase (인증 + DB, RLS)
- Pretendard (CDN), 프레임워크 없는 CSS 변수 디자인 토큰

## 시작하기

```sh
npm install
cp .env.example .env   # Supabase URL/키 입력
npm run dev
```

### Supabase 설정

1. [supabase.com](https://supabase.com)에서 프로젝트 생성
2. Dashboard > SQL Editor에 `supabase/schema.sql` 전체 붙여넣기 → Run
3. Dashboard > Settings > API의 URL과 anon key를 `.env`에 입력
4. Dashboard > Authentication > Sign In / Up에서 **Anonymous sign-ins** 활성화 (필수 — 익명 세션 자동 생성에 사용)

```
PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

## 화면

| 라우트 | 설명 |
| --- | --- |
| `/` | 홈 — 오늘의 복약 진행률, 다음 복용, 시간대별 체크리스트 |
| `/calendar` | 월간 캘린더 — 날짜별 복약 달성 도트, 선택 날짜 기록 |
| `/camera` | 약봉투 촬영·분석 — 약마다 여러 장 촬영(정확도↑)→완료, 약 추가로 여러 약 수집→약 확인하기로 상호작용·위험도 분석, 선택 추가 |
| `/settings` | 프로필(닉네임), 내 약 관리 |

로그인 화면은 없습니다. 앱 실행 시 Supabase 익명 세션이 자동 생성되어 기기별로 데이터가 저장됩니다.

## 데이터 모델

- `medications` — 약 (이름, 용량, 복용 시간대 `morning|noon|evening|night`, 기간, 색상, 메모)
- `medication_logs` — 복용 기록 (약 × 날짜 × 시간대, unique)
- `profiles` — 닉네임 (가입 시 트리거로 자동 생성)

## 남은 일

- [x] 약봉투 AI 분석 연동 — `앱 개발/server.py`(FastAPI) 띄우고 `.env`의 `PUBLIC_ANALYZE_API` 설정. 미설정 시 `analysis.ts` 목업으로 데모
- [ ] 복약 알림 (푸시/PWA)
- [ ] 배포 어댑터 결정 (현재 adapter-auto)
