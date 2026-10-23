# Backend (FastAPI). Heavy AI deps are opt-in via build arg INSTALL_AI.
ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Optional heavy AI stack (paddleocr/easyocr/torch/spacy). Default off so the
# image stays small; the app runs without it (OCR endpoints report failure).
ARG INSTALL_AI=false
COPY requirements-ai.txt ./
RUN if [ "$INSTALL_AI" = "true" ]; then pip install -r requirements-ai.txt; fi

COPY app ./app
COPY scripts ./scripts

RUN mkdir -p uploads/prescriptions && touch uploads/.gitkeep

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
