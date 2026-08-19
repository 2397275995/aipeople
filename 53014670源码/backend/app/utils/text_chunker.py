"""
文本分块工具。

将长文档按固定字符窗口切分，相邻块之间保留 overlap 重叠，
避免语义在块边界处被截断，提升 RAG 检索召回质量。
"""

from __future__ import annotations


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    按字符数滑动窗口切分文本。

    Args:
        text: 原始文本（已去除首尾空白）
        chunk_size: 每块最大字符数
        overlap: 相邻块重叠字符数，须小于 chunk_size

    Returns:
        非空文本块列表
    """
    text = text.strip()
    if not text:
        return []

    if overlap >= chunk_size:
        raise ValueError("overlap 必须小于 chunk_size")

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= text_len:
            break
        start = end - overlap

    return chunks
