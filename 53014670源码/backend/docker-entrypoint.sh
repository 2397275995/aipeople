#!/bin/bash
set -euo pipefail

cd /app

echo ">>> 执行向量库与资料初始化..."
python docker_init.py

echo ">>> 启动 FastAPI (uvicorn)..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-1}"
