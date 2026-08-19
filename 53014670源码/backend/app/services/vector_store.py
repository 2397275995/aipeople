"""
向量库公共模块。

封装 Chroma 持久化客户端与 SentenceTransformer 嵌入函数，
供 RAG 检索服务与 init_vector_store 初始化脚本共用，保证索引/查询使用同一套配置。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import os

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedding_function() -> SentenceTransformerEmbeddingFunction:
    """
    懒加载 sentence-transformers 嵌入模型。

    默认使用 BAAI/bge-m3，首次加载会下载模型权重，耗时较长属正常现象。
    """
    model_name = settings.EMBEDDING_MODEL
    # 兼容配置里写 "bge-m3" 的简写
    if model_name == "bge-m3":
        model_name = "BAAI/bge-m3"

    hf_endpoint = settings.ASR_HF_ENDPOINT or "https://hf-mirror.com"
    os.environ.setdefault("HF_ENDPOINT", hf_endpoint)
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", "/root/.cache/huggingface/hub")

    return SentenceTransformerEmbeddingFunction(model_name=model_name)


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    """获取 Chroma 持久化客户端，数据目录由 CHROMA_PERSIST_DIR 配置。"""
    persist_dir = Path(settings.CHROMA_PERSIST_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir))


def get_collection(*, reset: bool = False) -> Collection:
    """
    获取（或重建）景区知识库 Collection。

    Args:
        reset: True 时删除已有集合并重新创建（仅初始化脚本使用）
    """
    client = get_chroma_client()
    name = settings.CHROMA_COLLECTION_NAME

    if reset:
        try:
            client.delete_collection(name=name)
        except Exception:
            # 集合不存在时忽略
            pass

    return client.get_or_create_collection(
        name=name,
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def distance_to_confidence(distance: float) -> float:
    """
    将 Chroma 返回的余弦距离映射为 [0, 1] 置信度。

    cosine distance 理论范围 [0, 2]，越小表示越相似。
    """
    return max(0.0, min(1.0, 1.0 - distance / 2.0))
