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

import json
import os
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from inference import DrugNameNormalizer, load_pipeline

DB_PATH = os.getenv("DRUG_DB", "drug_data.db")
MODEL_PATH = os.getenv("DDI_MODEL", "ddi_model.pt")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # 있으면 미식별 항목 폴백 매칭에 사용

# ddi_model.pt가 있으면 DB 미등록 조합도 추정, 없으면 DB 조회만
# GEMINI_API_KEY가 있으면 DB·fuzzy로 못 찾은 약도 Gemini로 한 번 더 시도
analyzer = load_pipeline(
    DB_PATH,
    MODEL_PATH if os.path.exists(MODEL_PATH) else None,
    GEMINI_API_KEY,
)

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
    return {"ok": True, "gemini": gemini_status()}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """
    inference.py의 analyze() 결과를 그대로 반환:
      { identified, unidentified, interactions, drug_risk_score }
    """
    return analyzer.analyze(req.names)


# ── OCR (사진 → 약품명) ────────────────────────────────────
# GEMINI_API_KEY가 있으면 Gemini 비전으로 사진에서 약품명을 직접 읽는다
# (한글 약봉투 인식률이 EasyOCR보다 훨씬 높음). 없거나 실패하면 EasyOCR 폴백.
_gemini_client = None
_last_gemini_error: str | None = None  # 마지막 Gemini 호출 실패 원인 (진단용)
_gemini_model_ok: str | None = None    # 한 번 성공한 모델명 캐시


def _get_gemini():
    global _gemini_client
    if _gemini_client is None and GEMINI_API_KEY:
        from google import genai  # pip install google-genai

        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


def _candidate_models() -> list[str]:
    """
    시도할 모델명 후보. 구모델이 신규 키에서 404 나는 문제(예: gemini-2.5-flash
    'no longer available to new users') 대응 — 최신 별칭을 먼저 쓰고,
    안 되면 이 키로 실제 사용 가능한 flash 계열을 API에서 조회해 시도한다.
    """
    if _gemini_model_ok:
        return [_gemini_model_ok]
    cands = []
    if os.getenv("GEMINI_OCR_MODEL"):
        cands.append(os.getenv("GEMINI_OCR_MODEL"))
    cands.append("gemini-flash-latest")  # 항상 최신 flash를 가리키는 별칭
    try:
        names = [m.name.split("/")[-1] for m in _get_gemini().models.list()]
        flash = sorted(
            (n for n in names if "flash" in n
             and not any(x in n for x in ("lite", "live", "tts", "image", "audio"))),
            reverse=True)  # 버전 문자열이 큰(새로운) 것부터
        cands += [n for n in flash if n not in cands][:3]
    except Exception as e:
        print(f"[GeminiOCR] 모델 목록 조회 실패: {e}")
    return cands


def _gemini_read_burst(images: list[str]) -> list[str] | None:
    """
    같은 약(봉투)을 찍은 사진 여러 장 → Gemini 비전 → 약품명 목록.
    실패(키 없음/네트워크/파싱)하면 None을 반환해 EasyOCR 폴백을 태운다.
    """
    client = _get_gemini()
    if client is None:
        return None

    import base64

    from google.genai import types

    parts = []
    for img in images[:4]:  # 버스트당 최대 4장 — 비용/지연 제한 (사진끼리 내용은 같음)
        b64 = img.split(",", 1)[-1]  # data URL 접두어 제거
        parts.append(types.Part.from_bytes(
            data=base64.b64decode(b64), mime_type="image/jpeg"))

    prompt = (
        "이 사진들은 한국 약국의 약봉투(또는 처방전/약 포장)를 같은 대상으로 여러 번 찍은 것입니다. "
        "사진에 보이는 모든 의약품 이름(제품명)을 JSON 문자열 배열로 반환하세요.\n"
        "- 제품명만: 용량(mg 등)·개수·복용횟수·약물코드·날짜·병원/약국명·환자명은 제외\n"
        "- 같은 약이 여러 사진에 보여도 한 번만\n"
        "- 글자가 일부 흐려도 문맥상 확실하면 올바른 제품명으로 보정해서 적기\n"
        "- 의약품이 하나도 안 보이면 []\n"
        '형식 예: ["타이레놀정", "아모크라정"]'
    )
    global _last_gemini_error, _gemini_model_ok
    for model in _candidate_models():
        resp = None
        try:
            resp = client.models.generate_content(
                model=model,
                contents=parts + [prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": list[str],  # 모델이 배열 형태를 벗어나지 못하게 강제
                },
            )
            raw_text = resp.text  # 안전필터 차단 등으로 여기서도 예외가 날 수 있음
            names = _parse_json_array(raw_text)
            if names is not None:
                _last_gemini_error = None
                if _gemini_model_ok != model:
                    _gemini_model_ok = model
                    print(f"[GeminiOCR] 사용 모델: {model}")
                    # 성분 매칭 폴백(GeminiDrugMatcher)도 같은 모델을 쓰도록 동기화
                    if analyzer.llm_matcher is not None:
                        analyzer.llm_matcher.model = model
                return [str(n).strip() for n in names if str(n).strip()]
            _last_gemini_error = f"unexpected response: {raw_text[:300]!r}"
        except Exception as e:
            try:
                snippet = f" | raw={resp.text[:300]!r}" if resp is not None else ""
            except Exception:
                snippet = ""  # resp.text 접근 자체가 실패(예: 안전필터 차단)
            _last_gemini_error = f"{type(e).__name__}: {e}{snippet}"
            print(f"[GeminiOCR] {model} 실패: {_last_gemini_error}")
            if "404" not in str(e) and "NOT_FOUND" not in str(e):
                break  # 모델 없음(404)만 다음 후보 시도, 그 외(쿼터 등)는 중단
    return None


def _parse_json_array(text: str) -> list | None:
    """
    response_schema로 배열을 강제해도 가끔 코드펜스(```json ... ```)나 앞뒤
    잡설이 섞여 곧바로 json.loads가 실패하는 경우가 있다 — 흔한 변형을 몇 가지
    더 시도해보고, 그래도 안 되면 None(에러 메시지에 원문을 남겨 다음에
    바로 원인을 볼 수 있게 함).
    """
    if not text:
        return None
    candidates = [text.strip()]
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        candidates.append(fenced.group(1).strip())
    bracketed = re.search(r"\[.*\]", text, re.S)
    if bracketed:
        candidates.append(bracketed.group(0))
    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            return data
    return None


def _read_burst(images: list[str]) -> list[str]:
    """버스트 1개 → 약품명 목록. Gemini 비전 우선, 실패 시 EasyOCR 다수결."""
    names = _gemini_read_burst(images)
    if names is not None:
        return names
    return _vote_burst(images)


def gemini_status() -> str:
    """진단용: Gemini 사용 가능 여부. 'ok' | 'no-key' | 'init-error/call-error: ...'"""
    if not GEMINI_API_KEY:
        return "no-key"
    try:
        if _get_gemini() is None:
            return "no-key"
    except Exception as e:
        return f"init-error: {type(e).__name__}: {e}"
    if _last_gemini_error:
        return f"call-error: {_last_gemini_error}"
    return "ok"


def read_items(bursts: list[list[str]]) -> list[list[str]]:
    """약별 버스트 목록을 병렬로 읽는다 (Gemini 호출은 I/O 대기라 스레드로 겹치면 빠름)."""
    if len(bursts) <= 1:
        return [_read_burst(b) for b in bursts]
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=min(4, len(bursts))) as ex:
        return list(ex.map(_read_burst, bursts))


# EasyOCR은 무겁고 첫 실행 시 모델을 내려받으므로 lazy 로딩.
_reader = None


_norm = DrugNameNormalizer()


def _patch_no_pin_memory():
    """
    ZeroGPU: torch가 CUDA 빌드라 CUDA가 '보이지만' 실제 GPU가 미할당(CPU 실행)이면,
    easyocr 내부 DataLoader의 pin_memory 가 "No CUDA GPUs are available"로 터진다.
    → 모든 DataLoader의 pin_memory 를 강제로 끈다 (CPU 추론이라 성능 영향 없음).
    """
    import torch.utils.data as tud

    if getattr(tud.DataLoader, "_pin_patched", False):
        return
    _orig = tud.DataLoader.__init__

    def _init(self, *args, **kwargs):
        kwargs["pin_memory"] = False
        _orig(self, *args, **kwargs)

    tud.DataLoader.__init__ = _init
    tud.DataLoader._pin_patched = True


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr  # pip install easyocr (torch 재사용, 한글+영문)

        _patch_no_pin_memory()
        _reader = easyocr.Reader(["ko", "en"], gpu=False)
    return _reader


# 약봉투 OCR 잡음 필터 — 처방전 메타데이터(번호/날짜/페이지/약물코드)는
# 약 이름이 아니므로 analyze() 에 보내지 않는다. 안전 위주(오탐 시 실제
# 약 이름을 놓칠 수 있는 규칙은 넣지 않음 — 예: 순수 한글 이름 줄은 제외 안 함).
_NOISE_PATTERNS = [
    re.compile(r"처방|접수"),                      # "처방 : 26-04-21" 등 라벨
    re.compile(r"^\d{1,3}\s*/\s*\d{1,3}$"),         # 페이지 번호 "2/5"
    re.compile(r"^\d{2}[-.]\d{2}[-.]\d{2}(\s+\d{1,2}:\d{2}(:\d{2})?)?$"),  # 날짜/시각
    re.compile(r"^[A-Za-z0-9]+[-:.][A-Za-z0-9]+([-:.][A-Za-z0-9]+)?$"),  # "DIA-2339", "071-7113:D"(OCR이 :→.로 오독하기도 함)
    re.compile(r"^[A-Z]{2,6}$"),                    # 순수 영문 코드 "ATC","DACTC","DLTRA"
]


def _is_noise_line(raw: str) -> bool:
    s = raw.strip()
    return any(p.search(s) for p in _NOISE_PATTERNS)


# 약봉투 한 줄에 "코드  상품명 용량 개수 횟수"가 함께 붙어 나오는 경우
# (예: "DULTRA   울트라셋정 37.5/325mg ta 1  3  1") 앞의 코드가 그대로 남으면
# inference.py 의 fuzzy 매칭이 전체 문자열 유사도(SequenceMatcher/token_sort_ratio)를
# 쓰기 때문에 실제 상품명("울트라셋")과의 유사도가 떨어져 매칭에 실패한다.
# → 우리 쪽에서 앞의 코드 토큰만 잘라내 순수 상품명 위주로 넘긴다.
_LEADING_CODE = re.compile(r"^[A-Z]{2,8}\s{1,}(?=\S)")


def _strip_leading_code(s: str) -> str:
    return _LEADING_CODE.sub("", s, count=1)


# 용량/용법 꼬리(예: "37.5/325mg ta 1  3  1")가 남으면 inference.py의 normalize()가
# 숫자와 정/mg 등은 지워도 "/"나 "ta"(정제 약어, FORM 목록에 없음) 같은 잔여 기호는
# 남겨, 짧은 상품명 대비 전체 문자열 유사도가 떨어져 fuzzy 매칭이 실패한다.
# → 상품명 뒤에 숫자나 "/"가 처음 나오는 지점에서 잘라 순수 이름만 남긴다.
_DOSE_TAIL = re.compile(r"\s*[\d/].*$")


def _strip_dose_tail(s: str) -> str:
    return _DOSE_TAIL.sub("", s).strip()


def _preprocess(img):
    """
    약봉투 OCR 정확도용 전처리.
      - 그레이스케일: 배경 색/무늬 영향 제거
      - autocontrast: 반사광·저대비로 흐려진 글자의 명암을 넓게 편다 (가장 큰 효과)
      - 업스케일: 글씨가 작으면 키워서 인식 (긴 변 기준 최소 1600px)
      - unsharp mask: 작은 한글 글자의 획 경계를 또렷하게 해 검출 누락을 줄인다
    """
    from PIL import Image, ImageFilter, ImageOps

    img = img.convert("L")
    img = ImageOps.autocontrast(img, cutoff=1)
    long_side = max(img.size)
    if long_side < 1600:
        s = 1600 / long_side
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=2))
    return img.convert("RGB")  # readtext 호환(3채널)


def _ocr(image_b64: str) -> list[str]:
    import base64
    import io

    import numpy as np
    from PIL import Image

    raw = image_b64.split(",", 1)[-1]  # data URL 접두어 제거
    img = Image.open(io.BytesIO(base64.b64decode(raw)))
    img = _preprocess(img)
    lines = _get_reader().readtext(
        np.array(img),
        detail=0,
        paragraph=False,
        mag_ratio=1.8,        # 작은 글씨를 확대해 검출
        contrast_ths=0.05,    # 저대비 영역은 대비를 조정해 재인식
        adjust_contrast=0.7,
        text_threshold=0.5,   # 텍스트 검출 문턱 더 낮춤 (기본 0.7) — 흐린 줄 누락 방지
        low_text=0.25,        # 흐린 글자 경계까지 포함 (기본 0.4)
        link_threshold=0.35,  # 한글+영문+숫자가 섞인 줄을 하나로 잘 이어붙이도록 (기본 0.4)
    )
    lines = [ln for ln in lines if not _is_noise_line(ln)]
    lines = [_strip_dose_tail(_strip_leading_code(ln)) for ln in lines]
    return [ln for ln in lines if ln]


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
    """약봉투 사진 1장(base64) → OCR(Gemini 비전 우선) → analyze()."""
    try:
        lines = _read_burst([req.image])
    except ImportError:
        return _ocr_unavailable()
    result = analyzer.analyze(lines)
    result["ocr_lines"] = lines
    return result


@app.post("/analyze-images")
def analyze_images(req: MultiRequest):
    """
    약별 버스트 목록 → 약마다 이름 추출(Gemini 비전 우선, EasyOCR 폴백)
    → 모든 약품명 합쳐 analyze(). 앱의 '여러 번 찍기' 플로우가 부르는 엔드포인트.
    """
    if _get_gemini() is None:
        try:
            _get_reader()  # Gemini 없으면 EasyOCR이 필수
        except ImportError:
            return _ocr_unavailable()

    per_item = read_items([item.images for item in req.items])
    all_names = [n for names in per_item for n in names]

    result = analyzer.analyze(all_names)
    result["per_item_names"] = per_item  # 약별 인식 결과(디버그/확인용)
    result["gemini"] = gemini_status()   # 진단용: 키 미설정/오류를 응답에서 바로 확인
    return result


def _ocr_unavailable() -> dict:
    return {
        "error": "OCR 미설치 — pip install easyocr",
        "identified": {}, "unidentified": [],
        "interactions": [], "drug_risk_score": 0.0, "ocr_lines": [],
    }
