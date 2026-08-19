FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_PREFER_BINARY=1 \
    HF_HOME=/root/.cache/huggingface \
    HF_ENDPOINT=https://hf-mirror.com \
    HUGGINGFACE_HUB_CACHE=/root/.cache/huggingface/hub \
    ANONYMIZED_TELEMETRY=False

# 不安装 apt 编译工具，依赖 pip 预编译 wheel（避免 Debian 源网络失败）
COPY requirements.txt .
RUN pip install --upgrade pip \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --timeout 120 \
        --retries 10 \
    && pip install -r requirements.txt \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --timeout 120 \
        --retries 10 \
        --resume-retries 10

COPY . .

RUN python - <<'PY'
from pathlib import Path
path = Path('docker-entrypoint.sh')
path.write_text(path.read_text().replace('\r\n', '\n'), encoding='utf-8')
PY
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
