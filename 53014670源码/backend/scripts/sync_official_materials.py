#!/usr/bin/env python3
"""
同步官方资料包 → scenic_docs → 生成 POI → 重建向量库。

本地开发在 backend/ 目录执行：
    python scripts/sync_official_materials.py
    python scripts/sync_official_materials.py --reset
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.demo_materials import sync_official_materials, validate_official_docs  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="同步官方示范景区资料包并初始化数据")
    parser.add_argument("--reset", action="store_true", help="清空并重建向量索引")
    parser.add_argument("--skip-index", action="store_true", help="仅同步文件与 POI，不建向量库")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("同步官方「示范景区公开资料包」")
    logger.info("=" * 60)

    copied = sync_official_materials()
    validate_official_docs()

    extract_script = BACKEND_ROOT / "scripts" / "extract_official_data.py"
    subprocess.run([sys.executable, str(extract_script)], check=True, cwd=BACKEND_ROOT)

    if args.skip_index:
        logger.info("跳过向量库索引（--skip-index）")
        return

    index_cmd = [sys.executable, str(BACKEND_ROOT / "init_vector_store.py")]
    if args.reset:
        index_cmd.append("--reset")
    subprocess.run(index_cmd, check=True, cwd=BACKEND_ROOT)

    logger.info("全部完成。资料来源: 示范景区公开资料包（同步 %d 个文件）", copied)


if __name__ == "__main__":
    main()
