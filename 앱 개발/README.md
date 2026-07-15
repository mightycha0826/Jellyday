---
title: JellyDay DDI API
emoji: 💊
colorFrom: blue
colorTo: indigo
sdk: gradio
app_file: app.py
pinned: false
---

# JellyDay DDI API

약봉투 사진 → OCR → 약 식별 · 상호작용(DDI) · 위험도 분석 서비스.
알약 복약 관리 앱(pill-app)이 호출하는 백엔드 (Gradio API).

## API (앱이 호출)
Gradio REST 2-step 호출:
1. `POST /gradio_api/call/analyze_images` — body `{"data": [items]}` → `{"event_id": ...}`
2. `GET /gradio_api/call/analyze_images/<event_id>` — SSE, 완료 시 결과

`items` = `[{"images": ["data:image/...;base64,...", ...]}, ...]` (약별 버스트 목록)
응답: `{ identified, unidentified, interactions, drug_risk_score, per_item_names }`

`analyze_names` 엔드포인트는 OCR 없이 약품명만으로 테스트할 때 사용.

## 환경변수
- `DRUG_DB` (기본 `drug_data.db`), `DDI_MODEL` (기본 `ddi_model.pt`)
- `GEMINI_API_KEY` — 설정하면 (1) 사진에서 약품명을 Gemini 비전으로 직접 읽고
  (한글 인식률이 EasyOCR보다 훨씬 높음, 실패 시 EasyOCR 폴백),
  (2) DB·fuzzy로도 식별 못한 약을 Gemini로 한 번 더 성분 매칭한다
  (등록된 성분 목록 중에서만 고르게 해 환각을 제한).
  HF Spaces라면 Settings > Repository secrets에 등록. 없으면 기존 동작(EasyOCR + DB/fuzzy)으로 동작.
- `GEMINI_OCR_MODEL` — 비전 OCR에 쓸 모델 (기본: `gemini-flash-latest`,
  404 시 키로 사용 가능한 flash 모델을 자동 탐색)

## product_alias 커버리지 확장 (`build_product_alias.py`)
DUR(병용금기/용량주의/투여기간주의) 원본은 "특별히 주의가 필요한" 성분만 다뤄서
`ingredients` 테이블이 작다(303개). 반면 식약처 공공데이터포털의 "의약품 제품
허가정보"(`DrugPrdtPrmsnInfoService07`) API는 허가받은 전체 의약품(4만여 건)의
품목명↔주성분을 제공해서, DUR 경고 여부와 무관하게 실제 시중 약 이름을 알아보는
`product_alias` 테이블을 훨씬 넓게 채울 수 있다.

```
data.go.kr 마이페이지에서 이 API("의약품 제품 허가정보") 활용신청 승인 후:
MFDS_API_KEY=발급받은키 python build_product_alias.py drug_data.db
```

실행 전 `drug_data.db.bak`으로 자동 백업하며, 이미 있는 별칭은 덮어쓰지 않고
새 것만 추가한다(안전 수치가 필요한 `ingredients` 테이블은 이 API로 채우지
않음 — 그 값은 DUR 자료의 역할이라 여기서 추정해 넣지 않는다).
