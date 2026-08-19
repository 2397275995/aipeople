#!/usr/bin/env python3
"""
向量库初始化脚本。

用法（在 backend/ 目录下执行）：
    python init_vector_store.py
    python init_vector_store.py --reset          # 清空重建
    python init_vector_store.py --docs-dir ./data/scenic_docs

功能：
    1. 扫描 data/scenic_docs/ 下所有 .txt / .md / .pdf / .docx 文件
    2. 按 chunk_size=500, overlap=50 分块
    3. 使用 sentence-transformers (BAAI/bge-m3) 向量化
    4. 写入 Chroma 持久化向量库
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# 确保 backend/ 在 Python 路径中
BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.rag_service import RAGService  # noqa: E402
from app.services.vector_store import get_collection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="初始化景区知识库向量索引")
    parser.add_argument(
        "--docs-dir",
        default=settings.SCENIC_DOCS_DIR,
        help=f"景区文档目录（默认: {settings.SCENIC_DOCS_DIR}）",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="删除已有 Chroma 集合并重建（慎用）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    docs_dir = Path(args.docs_dir)

    logger.info("=" * 60)
    logger.info("景区知识库向量索引初始化")
    logger.info("  文档目录   : %s", docs_dir.resolve())
    logger.info("  向量库路径 : %s", Path(settings.CHROMA_PERSIST_DIR).resolve())
    logger.info("  集合名称   : %s", settings.CHROMA_COLLECTION_NAME)
    logger.info("  嵌入模型   : %s", settings.EMBEDDING_MODEL)
    logger.info("  分块参数   : size=%d overlap=%d", settings.RAG_CHUNK_SIZE, settings.RAG_CHUNK_OVERLAP)
    logger.info("  重建模式   : %s", args.reset)
    logger.info("=" * 60)

    if not docs_dir.exists():
        logger.error("文档目录不存在: %s", docs_dir.resolve())
        logger.error("请先运行: python scripts/sync_official_materials.py")
        logger.error("并将官方「示范景区公开资料包」解压到项目根目录")
        sys.exit(1)

    try:
        total = RAGService.index_directory(docs_dir, reset=args.reset)
        collection = get_collection()
        logger.info("✅ 初始化完成！共写入 %d 个文本块，集合总量 %d", total, collection.count())
    except FileNotFoundError as exc:
        logger.error("❌ %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("❌ 初始化失败: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
