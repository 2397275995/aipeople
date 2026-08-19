"""
官方「示范景区公开资料包」同步与校验。

所有 RAG 知识库与 POI 数据必须来源于该目录，禁止依赖项目内手写占位文档。
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# 早期开发占位文件（非官方资料，同步时移除）
PLACEHOLDER_FILENAMES = frozenset(
    {
        "主要景点介绍.md",
        "景区历史简介.md",
        "开放信息与游览指南.txt",
    }
)

OFFICIAL_EXTENSIONS = frozenset({".docx", ".xlsx", ".pdf", ".txt", ".md"})


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def find_official_package_dir(root: Path | None = None) -> Path:
    """定位官方资料包目录，优先使用 Docker 挂载目录。"""
    import os

    candidates: list[Path] = []

    env_dir = os.environ.get("OFFICIAL_PACKAGE_DIR")
    if env_dir:
        candidates.append(Path(env_dir))

    candidates.append(Path("/demo-materials"))
    root = root or project_root()
    candidates.append(root / "示范景区公开资料包")

    for candidate in candidates:
        if not candidate.is_dir():
            continue
        official = [
            f for f in candidate.iterdir() if f.is_file() and f.suffix.lower() in OFFICIAL_EXTENSIONS
        ]
        if official:
            return candidate

    for d in root.iterdir():
        if not d.is_dir() or d.name in {"backend", "web-client", "admin-web", "docker", "node_modules", ".git"}:
            continue
        if "资料" in d.name or "示范" in d.name:
            official = [f for f in d.iterdir() if f.is_file() and f.suffix.lower() in OFFICIAL_EXTENSIONS]
            if official:
                return d

    raise FileNotFoundError(
        "未找到官方资料包。请将资料解压到项目根目录的「示范景区公开资料包」，"
        "或确保 Docker 挂载目录 /demo-materials 中包含官方文档。"
    )


def scenic_docs_dir() -> Path:
    path = Path(settings.SCENIC_DOCS_DIR)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    return path


def remove_placeholders(docs_dir: Path) -> int:
    removed = 0
    for name in PLACEHOLDER_FILENAMES:
        p = docs_dir / name
        if p.is_file():
            p.unlink()
            removed += 1
            logger.info("已移除占位文档: %s", name)
    return removed


def sync_official_materials(
    *,
    src_dir: Path | None = None,
    dest_dir: Path | None = None,
    clean_placeholders: bool = True,
) -> int:
    """
    将官方资料包同步到 SCENIC_DOCS_DIR。

    Returns:
        新增或更新的文件数
    """
    src = src_dir or find_official_package_dir()
    dest = dest_dir or scenic_docs_dir()
    dest.mkdir(parents=True, exist_ok=True)

    if clean_placeholders:
        remove_placeholders(dest)

    copied = 0
    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        if src_file.suffix.lower() not in OFFICIAL_EXTENSIONS:
            continue
        rel = src_file.relative_to(src)
        dest_file = dest / rel
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        if not dest_file.exists() or src_file.stat().st_mtime > dest_file.stat().st_mtime:
            shutil.copy2(src_file, dest_file)
            copied += 1
            logger.info("同步官方资料: %s", rel)

    logger.info("官方资料同步完成，新增/更新 %d 个文件", copied)
    return copied


def list_official_files(docs_dir: Path | None = None) -> list[Path]:
    docs = docs_dir or scenic_docs_dir()
    if not docs.exists():
        return []
    return sorted(
        f
        for f in docs.rglob("*")
        if f.is_file() and f.suffix.lower() in OFFICIAL_EXTENSIONS and f.name not in PLACEHOLDER_FILENAMES
    )


def validate_official_docs(docs_dir: Path | None = None) -> None:
    """启动前校验：必须存在官方 docx。"""
    files = list_official_files(docs_dir)
    if not any(f.suffix.lower() == ".docx" for f in files):
        raise FileNotFoundError(
            "知识库目录缺少官方 docx 文件。请运行: python scripts/sync_official_materials.py"
        )
