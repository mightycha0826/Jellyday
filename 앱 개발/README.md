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
- `GEMINI_API_KEY` — 설정하면 DB·fuzzy로도 식별 못한 약을 Gemini로 한 번 더 시도한다
  (등록된 성분 목록 중에서만 고르게 해 환각을 제한). HF Spaces라면 Settings > Repository secrets에 등록.
  없으면 기존 동작(DB + fuzzy 매칭)만 그대로 동작한다.
