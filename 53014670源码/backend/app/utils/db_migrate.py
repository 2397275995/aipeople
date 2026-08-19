"""SQLite 轻量 schema 补丁（create_all 不修改已有表）。"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)


async def apply_sqlite_patches(conn: AsyncConnection) -> None:
    """为已有数据库补充新增列。"""
    result = await conn.execute(text("PRAGMA table_info(chat_messages)"))
    columns = {row[1] for row in result.fetchall()}

    if "sentiment" not in columns:
        await conn.execute(
            text("ALTER TABLE chat_messages ADD COLUMN sentiment VARCHAR(16)")
        )
        logger.info("已添加 chat_messages.sentiment 列")
