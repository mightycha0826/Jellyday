"""
HF Spaces (Gradio SDK, ZeroGPU) 진입점.

ZeroGPU 하드웨어는 `@spaces.GPU` 로 표시된 함수가 하나 이상 있어야 시작된다.
없으면 "No @spaces.GPU function detected during startup" 로 무조건 실패한다.
그래서 무거운 추론 함수(analyze_images_fn)에 데코레이터를 붙여 이 요구를 충족한다.

분석 로직(OCR + DDI)은 기존 server.py 함수를 재사용한다.
앱(pill-app)은 Gradio REST API 로 호출한다:
  POST /gradio_api/call/analyze_images   body: {"data": [items]}   → {"event_id": ...}
  GET  /gradio_api/call/analyze_images/<event_id>  (SSE) → 완료 시 결과
items = [{"images": ["dataURL", ...]}, ...] (약별 버스트 목록)
"""

import gradio as gr
import spaces

# server.py 의 로직 재사용: 로드된 파이프라인 + 버스트 다수결 OCR + OCR 리더
from server import analyzer, _vote_burst, _get_reader


@spaces.GPU(duration=120)
def analyze_images_fn(items):
    """약별 버스트 목록 → 약마다 다수결 OCR → 전체 합쳐 analyze()."""
    try:
        _get_reader()  # EasyOCR 준비 (미설치면 ImportError)
    except ImportError:
        return {
            "error": "OCR 미설치 — requirements 에 easyocr 필요",
            "identified": {}, "unidentified": [],
            "interactions": [], "drug_risk_score": 0.0, "per_item_names": [],
        }

    per_item, all_names = [], []
    for item in (items or []):
        names = _vote_burst(item.get("images", []))
        per_item.append(names)
        all_names.extend(names)

    result = analyzer.analyze(all_names)
    result["per_item_names"] = per_item  # 약별 인식 결과(디버그/확인용)
    return result


def analyze_names_fn(names_text):
    """OCR 없이 약품명(줄바꿈 구분)만으로 분석 — 데모/테스트용 (GPU 불필요)."""
    names = [n.strip() for n in (names_text or "").splitlines() if n.strip()]
    return analyzer.analyze(names)


with gr.Blocks(title="JellyDay DDI API") as demo:
    gr.Markdown(
        "## 💊 JellyDay DDI API\n"
        "약봉투 OCR → 약 식별 · 상호작용(DDI) · 위험도 분석 백엔드입니다. "
        "복약 관리 앱(pill-app)이 이 API 를 호출합니다."
    )

    # 앱이 호출하는 메인 엔드포인트 (api_name → /gradio_api/call/analyze_images)
    items_in = gr.JSON(label="items  (예: [{\"images\": [\"data:image/...;base64,...\"]}])")
    result_out = gr.JSON(label="result")
    gr.Button("analyze_images 실행").click(
        analyze_images_fn, items_in, result_out, api_name="analyze_images"
    )

    gr.Markdown("---\n#### 약품명으로 빠르게 테스트")
    names_in = gr.Textbox(label="약품명 (한 줄에 하나)", lines=3,
                          placeholder="타이레놀정\n아모크라정")
    names_out = gr.JSON(label="result")
    gr.Button("이름으로 분석").click(
        analyze_names_fn, names_in, names_out, api_name="analyze_names"
    )


demo.launch()
