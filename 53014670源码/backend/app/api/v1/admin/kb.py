"""
管理后台 — 知识库 API。
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import desc, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.deps import DbSession, get_current_admin
from app.core.security import create_admin_token
from app.models.knowledge import KnowledgeDocument
from app.schemas.admin import (
    AdminLoginData,
    AdminLoginRequest,
    KbDocumentItem,
    KbDocumentListData,
    KbDocumentStatusData,
    KbDocumentUploadData,
)
from app.schemas.chat import ApiResponse
from app.services.demo_materials import sync_official_materials, validate_official_docs
from app.services.document_processor import DocumentProcessor, SUPPORTED_EXTENSIONS
from app.services.rag_service import RAGService
from app.utils.response import success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin KB"])

_processor = DocumentProcessor()


async def _run_document_processing(
    doc_id: str,
    filename: str,
    content: bytes,
    category: str,
    scenic_area_id: str,
) -> None:
    """后台任务：使用独立 DB Session 处理文档。"""
    async with AsyncSessionLocal() as db:
        await _processor.process_document(
            db, doc_id, filename, content, category, scenic_area_id
        )


@router.post("/auth/login", response_model=ApiResponse[AdminLoginData])
async def admin_login(request: AdminLoginRequest) -> ApiResponse[AdminLoginData]:
    """
    管理员登录，返回 JWT Token。

    默认账号：admin / admin123
    也可直接使用硬编码 Token：Authorization: Bearer {ADMIN_API_TOKEN}
    """
    if request.username != settings.ADMIN_USERNAME or request.password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_admin_token()
    return success(
        AdminLoginData(
            token=token,
            expiresIn=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    )


@router.post("/kb/documents", response_model=ApiResponse[KbDocumentUploadData])
async def upload_kb_document(
    background_tasks: BackgroundTasks,
    db: DbSession,
    file: UploadFile = File(...),
    category: str = Form(default="other"),
    scenicAreaId: str = Form(default="lingshan_scenic"),
    _admin: str = Depends(get_current_admin),
) -> ApiResponse[KbDocumentUploadData]:
    """
    上传知识库文档，后台异步：解析 → 分块 → 向量化入库 Chroma。

    支持：PDF / TXT / MD / DOCX
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if f".{ext}" not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式 .{ext}，仅支持 pdf/txt/md/docx/xlsx",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    max_size = 20 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="文件大小不能超过 20MB")

    doc_id = _processor.make_doc_id(file.filename)
    title = file.filename.rsplit(".", 1)[0]

    doc = KnowledgeDocument(
        doc_id=doc_id,
        title=title,
        filename=file.filename,
        file_type=ext,
        category=category,
        scenic_area_id=scenicAreaId,
        status="pending",
        progress=0,
        chunk_count=0,
    )
    db.add(doc)
    await db.commit()

    background_tasks.add_task(
        _run_document_processing,
        doc_id,
        file.filename,
        content,
        category,
        scenicAreaId,
    )

    logger.info("文档已接收 doc_id=%s file=%s admin=%s", doc_id, file.filename, _admin)

    return success(
        KbDocumentUploadData(
            docId=doc_id,
            status="pending",
            chunkCount=0,
            progress=0,
        )
    )


@router.get("/kb/documents", response_model=ApiResponse[KbDocumentListData])
async def list_kb_documents(
    db: DbSession,
    limit: int = 20,
    _admin: str = Depends(get_current_admin),
) -> ApiResponse[KbDocumentListData]:
    """获取最近上传的知识库文档列表。"""
    result = await db.execute(
        select(KnowledgeDocument)
        .order_by(desc(KnowledgeDocument.created_at))
        .limit(min(limit, 100))
    )
    rows = result.scalars().all()

    documents = [
        KbDocumentItem(
            docId=row.doc_id,
            title=row.title,
            filename=row.filename,
            category=row.category,
            scenicAreaId=row.scenic_area_id,
            status=row.status,
            progress=row.progress,
            chunkCount=row.chunk_count,
            createdAt=row.created_at.isoformat() if row.created_at else "",
            errorMessage=row.error_message,
        )
        for row in rows
    ]
    return success(KbDocumentListData(documents=documents))


@router.get(
    "/kb/documents/{doc_id}",
    response_model=ApiResponse[KbDocumentStatusData],
)
async def get_kb_document_status(
    doc_id: str,
    db: DbSession,
    _admin: str = Depends(get_current_admin),
) -> ApiResponse[KbDocumentStatusData]:
    """查询单个文档的处理进度与状态（供前端轮询）。"""
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.doc_id == doc_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    return success(
        KbDocumentStatusData(
            docId=row.doc_id,
            status=row.status,
            progress=row.progress,
            chunkCount=row.chunk_count,
            errorMessage=row.error_message,
        )
    )


@router.post("/kb/import-demo", response_model=ApiResponse[dict])
async def import_demo_package(
    reset: bool = False,
    _admin: str = Depends(get_current_admin),
) -> ApiResponse[dict]:
    """
    一键导入官方「示范景区公开资料包」：同步文件 → 生成 POI → 重建向量索引。
    """
    try:
        copied = sync_official_materials()
        validate_official_docs()

        backend_root = Path(__file__).resolve().parents[4]
        extract = backend_root / "scripts" / "extract_official_data.py"
        subprocess.run([sys.executable, str(extract)], check=True, cwd=backend_root)

        docs_dir = Path(settings.SCENIC_DOCS_DIR)
        if not docs_dir.is_absolute():
            docs_dir = backend_root / docs_dir
        chunks = RAGService.index_directory(docs_dir, reset=reset)

        return success(
            {
                "syncedFiles": copied,
                "indexedChunks": chunks,
                "scenicAreaId": settings.SCENIC_AREA_ID,
                "scenicAreaName": settings.SCENIC_AREA_NAME,
                "message": "官方资料包导入完成",
            }
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("导入官方资料包失败")
        raise HTTPException(status_code=500, detail=f"导入失败: {exc}") from exc
