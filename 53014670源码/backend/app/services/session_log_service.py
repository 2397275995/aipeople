"""
会话日志持久化服务。

/chat/ask 成功后通过 BackgroundTasks 异步写入 SQLite，
供数据大屏 analytics 统计使用。
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.session import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


async def log_chat_interaction(
    *,
    session_id: str,
    message_id: str,
    user_text: str,
    bot_text: str,
    input_type: str = "text",
    emotion_response: str | None = None,
    sentiment: str | None = None,
    confidence: float | None = None,
    latency_ms: int | None = None,
) -> None:
    """写入一条问答会话日志（独立 DB Session，供后台任务调用）。"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ChatSession).where(ChatSession.session_id == session_id)
            )
            chat_session = result.scalar_one_or_none()
            if chat_session is None:
                db.add(ChatSession(session_id=session_id))
            else:
                chat_session.updated_at = datetime.utcnow()

            db.add(
                ChatMessage(
                    message_id=message_id,
                    session_id=session_id,
                    user_text=user_text,
                    bot_text=bot_text,
                    input_type=input_type,
                    emotion_response=emotion_response,
                    sentiment=sentiment,
                    confidence=confidence,
                    latency_ms=latency_ms,
                )
            )
            await db.commit()
            logger.debug("会话日志已写入 session=%s message=%s", session_id, message_id)
    except Exception:
        logger.exception("会话日志写入失败 session=%s", session_id)
