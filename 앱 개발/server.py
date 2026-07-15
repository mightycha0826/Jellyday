"""
JellyDay DDI API — inference.py를 HTTP로 노출하는 얇은 래퍼.

앱(SvelteKit)은 PyTorch를 못 돌리므로, 이 파이썬 서비스를 띄우고
앱이 POST /analyze 만 호출한다. drug_data.db(+ ddi_model.pt)는 이 서버에만 둔다.

실행:
    pip install -r requirements.txt
    uvicorn server:app --reload --port 8000

확인:
    curl -X POST http://localhost:8000/analyze \
         -H "content-type: application/json" \
         -d '{"names": ["타이레놀정", "아모크라정"]}'
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from inference import DrugNameNormalizer, load_pipeline

DB_PATH = os.getenv("DRUG_DB", "drug_data.db")
MODEL_PATH = os.getenv("DDI_MODEL", "ddi_model.pt")

# ddi_model.pt가 있으면 DB 미등록 조합도 추정, 없으면 DB 조회만
analyzer = load_pipeline(DB_PATH, MODEL_PATH if os.path.exists(MODEL_PATH) else None)

app = FastAPI(title="JellyDay DDI API", version="1.0")

# 개발용: 모든 origin 허용. 배포 시엔 앱 도메인만 남길 것.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    names: list[str]  # OCR/입력된 약품명 목록


class ImageRequest(BaseModel):
    image: str  # data URL("data:image/...;base64,XXXX") 또는 순수 base64


class BurstItem(BaseModel):
    images: list[str]  # 같은 약(봉투)을 여러 번 찍은 사진들


class MultiRequest(BaseModel):
    items: list[BurstItem]  # 약별 버스트 목록


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """
    inference.py의 analyze() 결과를 그대로 반환:
      { identified, unidentified, interactions, drug_risk_score }
    """
    return analyzer.analyze(req.names)


# ── OCR (사진 → 약품명) ────────────────────────────────────
# EasyOCR은 무겁고 첫 실행 시 모델을 내려받으므로 lazy 로딩.
_reader = None


_norm = DrugNameNormalizer()


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr  # pip install easyocr (torch 재사용, 한글+영문)
        _reader = easyocr.Reader(["ko", "en"], gpu=False)
    return _reader


def _ocr(image_b64: str) -> list[str]:
    import base64
    import io

    import numpy as np
    from PIL import Image

    raw = image_b64.split(",", 1)[-1]  # data URL 접두어 제거
    img = Image.open(io.BytesIO(base64.b64decode(raw))).convert("RGB")
    return _get_reader().readtext(np.array(img), detail=0, paragraph=False)


def _vote_burst(images: list[str]) -> list[str]:
    """
    같은 약을 여러 장 찍은 버스트에서 신뢰도 높은 텍스트만 남긴다.
    각 사진을 OCR → 정규화 기준으로 다수결. 여러 장에서 반복 등장한 줄일수록
    실제 약품명일 확률이 높고, 한 장에서만 잘못 읽힌 노이즈는 걸러진다.
    """
    from collections import Counter

    n = len(images)
    votes: Counter = Counter()
    rep: dict = {}  # 정규화 키 → 대표 원본 줄
    for img in images:
        for line in set(_ocr(img)):
            key = _norm.normalize(line)
            if not key:
                continue
            votes[key] += 1
            rep.setdefault(key, line)

    threshold = (n // 2) + 1 if n >= 2 else 1  # 과반 등장만 채택
    names = [rep[k] for k, c in votes.items() if c >= threshold]
    return names or list(rep.values())  # 과반이 없으면 전체 사용(폴백)


@app.post("/analyze-image")
def analyze_image(req: ImageRequest):
    """약봉투 사진 1장(base64) → OCR → analyze()."""
    try:
        lines = _ocr(req.image)
    except ImportError:
        return _ocr_unavailable()
    result = analyzer.analyze(lines)
    result["ocr_lines"] = lines
    return result


@app.post("/analyze-images")
def analyze_images(req: MultiRequest):
    """
    약별 버스트 목록 → 약마다 다수결 OCR → 모든 약품명 합쳐 analyze().
    앱의 '여러 번 찍기' 플로우가 부르는 엔드포인트.
    """
    try:
        _get_reader()
    except ImportError:
        return _ocr_unavailable()

    per_item, all_names = [], []
    for item in req.items:
        names = _vote_burst(item.images)
        per_item.append(names)
        all_names.extend(names)

    result = analyzer.analyze(all_names)
    result["per_item_names"] = per_item  # 약별 인식 결과(디버그/확인용)
    return result


def _ocr_unavailable() -> dict:
    return {
        "error": "OCR 미설치 — pip install easyocr",
        "identified": {}, "unidentified": [],
        "interactions": [], "drug_risk_score": 0.0, "ocr_lines": [],
    }
