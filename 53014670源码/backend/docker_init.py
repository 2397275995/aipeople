#!/usr/bin/env python3
"""
Docker 容器启动前：同步官方资料包、生成 POI、初始化向量库。
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.demo_materials import sync_official_materials  # noqa: E402
from app.services.rag_service import RAGService  # noqa: E402
from app.services.vector_store import get_collection  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MARKER = Path("/app/data/.vector_initialized")
DOCKER_DEMO_SRC = Path("/demo-materials")


def sync_from_mount() -> int:
    """Docker 挂载的官方资料目录 → SCENIC_DOCS_DIR。"""
    if DOCKER_DEMO_SRC.exists() and any(DOCKER_DEMO_SRC.iterdir()):
        os.environ["OFFICIAL_PACKAGE_DIR"] = str(DOCKER_DEMO_SRC)
        return sync_official_materials(src_dir=DOCKER_DEMO_SRC)
    logger.warning("未挂载官方资料目录 %s，使用已有 scenic_docs", DOCKER_DEMO_SRC)
    return 0


def regenerate_pois() -> None:
    script = BACKEND_ROOT / "scripts" / "extract_official_data.py"
    env = os.environ.copy()
    if DOCKER_DEMO_SRC.exists() and any(DOCKER_DEMO_SRC.iterdir()):
        env["OFFICIAL_PACKAGE_DIR"] = str(DOCKER_DEMO_SRC)
    subprocess.run([sys.executable, str(script)], check=True, cwd=BACKEND_ROOT, env=env)


def needs_init() -> bool:
    force = os.environ.get("FORCE_REINDEX", "").lower() in ("1", "true", "yes")
    if force:
        return True
    if not MARKER.exists():
        return True
    try:
        return get_collection().count() == 0
    except Exception:
        return True


def main() -> None:
    logger.info("=" * 60)
    logger.info("Docker 启动：官方资料包初始化")
    logger.info("  挂载目录   : %s", DOCKER_DEMO_SRC)
    logger.info("  文档目录   : %s", settings.SCENIC_DOCS_DIR)
    logger.info("  向量库路径 : %s", settings.CHROMA_PERSIST_DIR)
    logger.info("=" * 60)

    sync_from_mount()
    regenerate_pois()

    if not needs_init():
        logger.info("向量库已存在，跳过索引（设置 FORCE_REINDEX=true 可强制重建）")
        return

    reset = os.environ.get("RESET_INDEX", "").lower() in ("1", "true", "yes")
    docs_dir = Path(settings.SCENIC_DOCS_DIR)
    if not docs_dir.is_absolute():
        docs_dir = BACKEND_ROOT / docs_dir

    total = RAGService.index_directory(docs_dir, reset=reset)
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.touch()
    logger.info("向量库初始化完成，写入 %d 个文本块", total)


if __name__ == "__main__":
    main()
