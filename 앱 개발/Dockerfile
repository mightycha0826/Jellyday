# JellyDay DDI API — Hugging Face Spaces (Docker SDK) 배포용
# HF Docker Space는 컨테이너의 7860 포트를 공개하고, UID 1000 사용자로 실행한다.
FROM python:3.10-slim

# EasyOCR/OpenCV 런타임에 필요한 시스템 라이브러리
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 libsm6 libxext6 && \
    rm -rf /var/lib/apt/lists/*

# HF Spaces 권장: 루트가 아닌 사용자로 실행 (파일/캐시 쓰기 권한 문제 방지)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

# torch는 CPU 전용 휠로 (CUDA 빌드 회피 → 이미지 수 GB 절약)
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# EasyOCR 한글/영문 모델을 '빌드 시점'에 미리 받아 이미지에 포함
# (HOME=/home/user 에 캐시되므로 런타임에도 그대로 재사용 → 콜드스타트 단축)
RUN python -c "import easyocr; easyocr.Reader(['ko','en'], gpu=False)"

# 서버 코드 + 데이터(drug_data.db, ddi_model.pt, inference.py 등)
COPY --chown=user . .

EXPOSE 7860
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
