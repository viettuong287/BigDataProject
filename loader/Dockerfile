# Image công cụ Python (loader, validate, build dashboard, đo latency).
# Máy Windows không cần cài Python: mọi script chạy trong container này.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /work
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

CMD ["python", "--version"]
