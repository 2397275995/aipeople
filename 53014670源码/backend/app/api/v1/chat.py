"""
问答 API 路由。

POST /api/v1/chat/ask — 景区数字人核心问答接口。
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.schemas.chat import ApiResponse, ChatAskData, ChatAskRequest
from app.services.chat_service import ChatService
from app.services.sentiment_service import classify_sentiment
from app.services.session_log_service import log_chat_interaction
from app.utils.response import success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# 进程级单例，避免每次请求重复加载嵌入模型
_chat_service = ChatService()


def get_chat_service() -> ChatService:
    return _chat_service


@router.post("/ask", response_model=ApiResponse[ChatAskData])
async def chat_ask(
    request: ChatAskRequest,
    background_tasks: BackgroundTasks,
    chat_service: ChatService = Depends(get_chat_service),
) -> ApiResponse[ChatAskData]:
    """
    核心问答接口（文本/语音共用）。

    流程：会话记忆 → Chroma RAG(top-3) → LLM → TTS → 写回会话记忆。

    响应结构符合 FSD 第 5.2 节：
    messageId, answerText, emotionTag, confidence, sources, tts, avatar
    """
    start = time.perf_counter()
    try:
        data = await chat_service.ask(request)
    except FileNotFoundError as exc:
        logger.error("向量库或文档未初始化: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="知识库尚未初始化，请先运行 python init_vector_store.py",
        ) from exc
    except Exception as exc:
        logger.exception("问答处理失败 session=%s", request.sessionId)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"问答处理失败: {exc}",
        ) from exc

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "chat/ask session=%s message=%s confidence=%.2f latency=%dms",
        request.sessionId,
        data.messageId,
        data.confidence,
        elapsed_ms,
    )

    # 异步写入 SQLite 会话日志，不阻塞响应
    user_sentiment = classify_sentiment(request.text)
    background_tasks.add_task(
        log_chat_interaction,
        session_id=request.sessionId,
        message_id=data.messageId,
        user_text=request.text,
        bot_text=data.answerText,
        input_type=request.inputType,
        emotion_response=data.emotionTag,
        sentiment=user_sentiment,
        confidence=data.confidence,
        latency_ms=elapsed_ms,
    )

    return success(data)
