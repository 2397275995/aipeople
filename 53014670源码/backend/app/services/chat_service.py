"""
核心问答编排服务。

串联：会话记忆读取 → RAG 检索 → LLM 生成 → TTS 合成 → 会话记忆写入，
返回符合 FSD 定义的完整 ChatAskData 结构。
"""

from __future__ import annotations

import logging

from app.schemas.chat import (
    AvatarPayload,
    ChatAskData,
    ChatAskRequest,
    SourceItem,
)
from app.services.llm_service import LLMService, merge_confidence
from app.services.rag_service import RAGService
from app.services.session_memory import session_memory
from app.services.tts_service import TTSService
from app.utils import generate_id

logger = logging.getLogger(__name__)


class ChatService:
    """景区数字人问答编排服务。"""

    def __init__(self) -> None:
        self.rag = RAGService()
        self.llm = LLMService()
        self.tts = TTSService()

    async def ask(self, request: ChatAskRequest) -> ChatAskData:
        """
        真实问答主流程。

        1. 读取 sessionId 对应最近 3 轮对话
        2. Chroma 检索 top-3 相关文档块
        3. 构造 Prompt 调用 LLM（Mock / OpenAI 兼容）
        4. TTS 合成语音与音素
        5. 写入会话记忆
        6. 组装 FSD 标准响应
        """
        message_id = generate_id("msg")

        # --- Step 1: 会话记忆 ---
        history = await session_memory.get_history(request.sessionId)
        logger.debug("session=%s history_len=%d", request.sessionId, len(history))

        # --- Step 2: RAG 检索 top-3 ---
        chunks = await self.rag.retrieve(request.text, top_k=3)
        sources = [
            SourceItem(docId=c["docId"], title=c["title"], snippet=c["snippet"])
            for c in chunks
        ]

        # --- Step 3: LLM 生成 ---
        llm_result = await self.llm.generate(
            question=request.text,
            context_chunks=chunks,
            history=history,
            preference=request.preference,
        )

        answer_text: str = llm_result["answerText"]
        emotion_tag: str = llm_result["emotionTag"]
        llm_confidence: float = llm_result["confidence"]

        # 综合 RAG + LLM 置信度
        if chunks:
            rag_conf = sum(c.get("confidence", 0.0) for c in chunks) / len(chunks)
            confidence = merge_confidence(rag_conf, llm_confidence)
        else:
            confidence = llm_confidence

        # --- Step 4: TTS 合成 ---
        tts_payload = await self.tts.synthesize(
            text=answer_text,
            message_id=message_id,
        )

        # --- Step 5: 更新会话记忆（最近 3 轮）---
        await session_memory.append_turn(
            session_id=request.sessionId,
            user_text=request.text,
            assistant_text=answer_text,
        )

        # --- Step 6: 组装响应 ---
        avatar_expression = _map_emotion_to_expression(emotion_tag)

        return ChatAskData(
            messageId=message_id,
            answerText=answer_text,
            emotionTag=emotion_tag,
            confidence=round(confidence, 2),
            sources=sources,
            tts=tts_payload,
            avatar=AvatarPayload(
                expression=avatar_expression,
                gesture="explain" if chunks else "idle",
            ),
        )


def _map_emotion_to_expression(emotion_tag: str) -> str:
    """将 LLM 情感标签映射为数字人表情名（供 Live2D Motion 选择）。"""
    mapping = {
        "friendly": "happy",
        "professional": "neutral",
        "excited": "happy",
        "curious": "think",
        "surprise": "surprise",
        "happy": "happy",
    }
    return mapping.get(emotion_tag, "happy")
