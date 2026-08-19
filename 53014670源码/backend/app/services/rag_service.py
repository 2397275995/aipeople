"""
RAG 知识检索服务。

基于 Chroma 向量库 + sentence-transformers 嵌入，从本地景区文档中
检索与用户问题最相关的文本块，供 LLM 生成回答时作为上下文引用。
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from app.core.config import settings
from app.services.vector_store import distance_to_confidence, get_collection
from app.utils.text_chunker import chunk_text


class RAGService:
    """景区知识库检索服务。"""

    def __init__(self, top_k: int | None = None) -> None:
        self.top_k = top_k or settings.RAG_TOP_K

    async def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        """
        异步检索与 query 最相似的文档块。

        嵌入与向量查询为 CPU/IO 密集型操作，通过 asyncio.to_thread
        放入线程池，避免阻塞 FastAPI 事件循环。

        Returns:
            list[dict]: 每项包含 docId, title, snippet, score, confidence
        """
        k = top_k or self.top_k
        return await asyncio.to_thread(self._retrieve_sync, query, k)

    def _retrieve_sync(self, query: str, top_k: int) -> list[dict]:
        collection = get_collection()
        count = collection.count()
        if count == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        chunks: list[dict] = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            meta = meta or {}
            confidence = distance_to_confidence(float(dist))
            chunks.append(
                {
                    "docId": meta.get("doc_id", "unknown"),
                    "title": meta.get("title", "未知文档"),
                    "snippet": (doc or "")[:200],
                    "content": doc or "",
                    "score": round(1.0 - float(dist) / 2.0, 4),
                    "confidence": round(confidence, 4),
                    "source_file": meta.get("source_file", ""),
                }
            )
        return chunks

    @staticmethod
    def index_directory(docs_dir: str | Path, *, reset: bool = False) -> int:
        """
        扫描目录下 txt/md 文件，分块后写入 Chroma。

        供 init_vector_store.py 调用；返回成功入库的 chunk 总数。
        """
        docs_path = Path(docs_dir)
        if not docs_path.exists():
            raise FileNotFoundError(f"文档目录不存在: {docs_path.resolve()}")

        collection = get_collection(reset=reset)
        patterns = ("*.txt", "*.md", "*.pdf", "*.docx", "*.xlsx")
        files: list[Path] = []
        for pattern in patterns:
            files.extend(sorted(docs_path.rglob(pattern)))

        if not files:
            raise FileNotFoundError(
                f"目录 {docs_path.resolve()} 下未找到可索引文件"
                f"（支持 .txt / .md / .pdf / .docx / .xlsx），请先同步「示范景区公开资料包」"
            )

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []

        for file_path in files:
            text = RAGService._read_file_text(file_path)
            if not text.strip():
                continue
            title = file_path.stem
            doc_id = hashlib.md5(str(file_path.resolve()).encode()).hexdigest()[:12]

            for idx, chunk in enumerate(
                chunk_text(
                    text,
                    chunk_size=settings.RAG_CHUNK_SIZE,
                    overlap=settings.RAG_CHUNK_OVERLAP,
                )
            ):
                chunk_id = f"{doc_id}_{idx}"
                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append(
                    {
                        "doc_id": doc_id,
                        "title": title,
                        "source_file": str(file_path.name),
                        "chunk_index": idx,
                    }
                )

        # Chroma 单次 add 有数量限制，分批写入
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            collection.add(
                ids=ids[i : i + batch_size],
                documents=documents[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )

        return len(ids)

    @staticmethod
    def _read_file_text(file_path: Path) -> str:
        """读取 txt/md/pdf/docx 为纯文本。"""
        ext = file_path.suffix.lower()
        if ext in (".txt", ".md"):
            return file_path.read_text(encoding="utf-8", errors="ignore")
        if ext in (".pdf", ".docx", ".xlsx"):
            from app.services.document_processor import DocumentProcessor

            return DocumentProcessor().parse_bytes(file_path.read_bytes(), file_path.name)
        raise ValueError(f"不支持的文件格式: {ext}")
