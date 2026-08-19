#!/usr/bin/env bash
# =============================================================================
# 景区导览 AI 数字人 — Docker Compose 一键部署
#
# 用法:
#   chmod +x deploy.sh && ./deploy.sh          # 首次部署 / 更新
#   ./deploy.sh --reindex                      # 强制重建向量库
#   ./deploy.sh --down                         # 停止并移除容器
#
# 依赖: Docker 20+、Docker Compose v2、Bash（Windows 请用 Git Bash / WSL）
# =============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

DEMO_DIR="$ROOT/示范景区公开资料包"
DOCS_DIR="$ROOT/backend/data/scenic_docs"
ENV_FILE="$ROOT/backend/.env"
FORCE_REINDEX="false"
RESET_INDEX="false"
ACTION="up"

log() { printf '\033[1;36m==>\033[0m %s\n" "$*"; }
warn() { printf '\033[1;33m!!>\033[0m %s\n" "$*"; }
err() { printf '\033[1;31mERR>\033[0m %s\n" "$*"; exit 1; }

usage() {
  cat <<'EOF'
用法: ./deploy.sh [选项]

选项:
  --reindex    强制重建向量库（保留旧数据，追加/更新索引）
  --reset      清空向量库后重建（等同 RESET_INDEX=true）
  --down       停止并移除容器（保留数据卷）
  --logs       查看服务日志
  -h, --help   显示帮助
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --reindex) FORCE_REINDEX="true"; shift ;;
    --reset)   FORCE_REINDEX="true"; RESET_INDEX="true"; shift ;;
    --down)    ACTION="down"; shift ;;
    --logs)    ACTION="logs"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) err "未知参数: $1（使用 --help 查看帮助）" ;;
  esac
done

# ---------------------------------------------------------------------------
# 前置检查
# ---------------------------------------------------------------------------
command -v docker >/dev/null 2>&1 || err "未找到 docker，请先安装 Docker"
docker compose version >/dev/null 2>&1 || err "未找到 docker compose，请安装 Docker Compose v2"

if [[ "$ACTION" == "down" ]]; then
  log "停止服务..."
  docker compose down
  log "已停止（数据卷 backend_data / redis_data 已保留）"
  exit 0
fi

if [[ "$ACTION" == "logs" ]]; then
  docker compose logs -f
  exit 0
fi

# ---------------------------------------------------------------------------
# 环境变量
# ---------------------------------------------------------------------------
log "检查环境变量..."
if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT/backend/.env.example" "$ENV_FILE"
  warn "已从 .env.example 生成 backend/.env，建议编辑后再部署"
fi

# ---------------------------------------------------------------------------
# 同步示范景区资料包到 backend/data/scenic_docs（宿主机备份，容器内也会挂载同步）
# ---------------------------------------------------------------------------
log "同步示范景区公开资料包..."
mkdir -p "$DOCS_DIR"

if [[ -d "$DEMO_DIR" ]] && find "$DEMO_DIR" -type f -print -quit 2>/dev/null | grep -q .; then
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "$DEMO_DIR"/ "$DOCS_DIR"/
  else
    cp -r "$DEMO_DIR"/. "$DOCS_DIR"/
  fi
  FILE_COUNT="$(find "$DOCS_DIR" -type f | wc -l | tr -d ' ')"
  log "已同步 $FILE_COUNT 个文件到 backend/data/scenic_docs"
else
  warn "未找到「示范景区公开资料包」或目录为空"
  warn "请将官方资料包解压到: $DEMO_DIR"
  if find "$DOCS_DIR" -type f -print -quit 2>/dev/null | grep -q .; then
    log "将使用 backend/data/scenic_docs 中已有文档"
  else
    err "没有可用的知识库文档，无法初始化向量库"
  fi
fi

# ---------------------------------------------------------------------------
# 构建 & 启动
# ---------------------------------------------------------------------------
export FORCE_REINDEX RESET_INDEX

log "构建镜像并启动服务（首次启动会下载嵌入模型，约 5~15 分钟）..."
docker compose up -d --build

log "等待后端健康检查..."
ATTEMPTS=0
MAX_ATTEMPTS=60
until docker compose exec -T backend python -c \
  "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" \
  >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if [[ $ATTEMPTS -ge $MAX_ATTEMPTS ]]; then
    warn "后端启动较慢，请稍后手动检查: docker compose logs backend"
    break
  fi
  sleep 5
done

HTTP_PORT="${HTTP_PORT:-80}"

cat <<EOF

================================================================================
部署完成！

  游客端（数字人） : http://localhost:${HTTP_PORT}/
  管理后台         : http://localhost:${HTTP_PORT}/admin/
  API 文档         : http://localhost:${HTTP_PORT}/docs
  健康检查         : http://localhost:${HTTP_PORT}/health

常用命令:
  docker compose logs -f          # 查看日志
  docker compose ps               # 查看状态
  ./deploy.sh --reindex           # 资料更新后重建向量库
  ./deploy.sh --down              # 停止服务

================================================================================
EOF
