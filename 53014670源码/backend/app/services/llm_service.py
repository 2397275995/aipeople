"""
大模型推理服务。

提供可替换的 LLM 客户端抽象：
  - MockLLMClient   : 无 API Key 时的本地 Mock，基于检索上下文拼接回答
  - OpenAIClient    : OpenAI 兼容接口（OpenAI / DeepSeek / 通义 / 智谱等）

通过环境变量 LLM_PROVIDER=mock|openai 切换实现。
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class LLMResult:
    """LLM 生成结果，与 FSD 响应字段对齐。"""

    answer_text: str
    emotion_tag: str = "friendly"
    confidence: float = 0.85


# ---------------------------------------------------------------------------
# Prompt 构造
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一名专业、亲切的灵山胜景 AI 数字人导游。
请严格依据「参考资料」（来自官方示范景区公开资料包）回答游客问题，不要编造资料中不存在的事实。
若参考资料不足以回答，请礼貌说明并建议游客咨询景区服务台。
回答控制在 80~200 字，语气自然、有温度。"""


def build_user_prompt(
    question: str,
    context_chunks: list[dict],
    history: list[dict[str, str]] | None = None,
    preference: list[str] | None = None,
) -> str:
    """
    构造发给 LLM 的用户 Prompt。

    包含：参考资料块、历史对话、兴趣偏好、当前问题。
    """
    # 1. 参考资料
    if context_chunks:
        ref_parts = []
        for i, chunk in enumerate(context_chunks, start=1):
            ref_parts.append(
                f"[{i}] 来源《{chunk.get('title', '未知')}》\n{chunk.get('content') or chunk.get('snippet', '')}"
            )
        references = "\n\n".join(ref_parts)
    else:
        references = "（暂无匹配的参考资料）"

    # 2. 历史对话
    history_text = ""
    if history:
        lines = [f"{m['role']}: {m['content']}" for m in history]
        history_text = "\n".join(lines)

    # 3. 兴趣偏好
    pref_text = ""
    if preference:
        pref_map = {
            "history": "历史文化",
            "culture": "人文艺术",
            "nature": "自然风光",
            "family": "亲子休闲",
        }
        labels = [pref_map.get(p, p) for p in preference]
        pref_text = f"游客兴趣偏好：{', '.join(labels)}"

    sections = [
        f"【参考资料】\n{references}",
    ]
    if history_text:
        sections.append(f"【历史对话】\n{history_text}")
    if pref_text:
        sections.append(pref_text)
    sections.append(f"【当前问题】\n{question}")

    return "\n\n".join(sections)


def merge_confidence(rag_confidence: float, llm_confidence: float) -> float:
    """综合 RAG 检索置信度与 LLM 自评置信度（加权平均）。"""
    if rag_confidence <= 0:
        return round(llm_confidence * 0.5, 2)
    return round(rag_confidence * 0.6 + llm_confidence * 0.4, 2)


# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------


class BaseLLMClient(ABC):
    """LLM 客户端抽象接口，便于替换不同厂商实现。"""

    @abstractmethod
    async def generate(
        self,
        question: str,
        context_chunks: list[dict],
        history: list[dict[str, str]] | None = None,
        preference: list[str] | None = None,
    ) -> LLMResult:
        ...


# ---------------------------------------------------------------------------
# Mock 实现（开发 / 无 API Key）
# ---------------------------------------------------------------------------


class MockLLMClient(BaseLLMClient):
    """
    本地 Mock LLM。

    不调用外部 API，直接基于 RAG 检索到的上下文拼接回答，
    用于开发调试、初赛演示及 CI 环境。
    """

    async def generate(
        self,
        question: str,
        context_chunks: list[dict],
        history: list[dict[str, str]] | None = None,
        preference: list[str] | None = None,
    ) -> LLMResult:
        _ = history, preference  # Mock 暂不使用多轮/偏好

        if not context_chunks:
            return LLMResult(
                answer_text=(
                    "抱歉，我在知识库中没有找到与您问题直接相关的信息。"
                    "您可以换个方式提问，或前往景区游客中心咨询工作人员。"
                ),
                emotion_tag="professional",
                confidence=0.35,
            )

        top = context_chunks[0]
        snippet = top.get("content") or top.get("snippet", "")
        title = top.get("title", "景区资料")

        answer = (
            f"根据《{title}》中的介绍，{snippet}"
            "如果您想深入了解，我可以为您推荐相关的游览路线。"
        )
        # 截断过长回答
        if len(answer) > 280:
            answer = answer[:277] + "…"

        avg_conf = sum(c.get("confidence", 0.5) for c in context_chunks) / len(
            context_chunks
        )

        return LLMResult(
            answer_text=answer,
            emotion_tag="friendly",
            confidence=round(min(0.95, avg_conf + 0.05), 2),
        )


# ---------------------------------------------------------------------------
# OpenAI 兼容实现
# ---------------------------------------------------------------------------


class OpenAIClient(BaseLLMClient):
    """
    OpenAI Chat Completions 兼容客户端。

    支持 OpenAI、DeepSeek、硅基流动、阿里云百炼等提供
    /v1/chat/completions 兼容接口的服务，通过 LLM_API_BASE 配置。
    """

    def __init__(self) -> None:
        self.api_key = settings.LLM_API_KEY
        self.api_base = settings.LLM_API_BASE.rstrip("/")
        self.model = settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT

    async def generate(
        self,
        question: str,
        context_chunks: list[dict],
        history: list[dict[str, str]] | None = None,
        preference: list[str] | None = None,
    ) -> LLMResult:
        if not self.api_key:
            logger.warning("LLM_API_KEY 未配置，回退到 MockLLMClient")
            return await MockLLMClient().generate(
                question, context_chunks, history, preference
            )

        user_prompt = build_user_prompt(question, context_chunks, history, preference)

        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 将历史对话转为 OpenAI messages 格式
        if history:
            for msg in history:
                role = "assistant" if msg["role"] == "assistant" else "user"
                messages.append({"role": role, "content": msg["content"]})

        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 512,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("LLM 请求失败 base=%s model=%s: %s", self.api_base, self.model, exc)
                raise RuntimeError(
                    f"大模型 API 调用失败（{self.api_base}），请检查 LLM_API_BASE / LLM_API_KEY / 网络"
                ) from exc
            data = resp.json()

        answer_text = data["choices"][0]["message"]["content"].strip()

        # 估算置信度：有检索结果时基于 top-1 相似度，否则偏低
        if context_chunks:
            rag_conf = context_chunks[0].get("confidence", 0.5)
            confidence = merge_confidence(rag_conf, 0.88)
        else:
            confidence = 0.45

        emotion_tag = _infer_emotion(answer_text)

        return LLMResult(
            answer_text=answer_text,
            emotion_tag=emotion_tag,
            confidence=confidence,
        )


def _infer_emotion(text: str) -> str:
    """简单规则推断回答情感标签（后续可换情感分类模型）。"""
    if re.search(r"抱歉|很遗憾|无法", text):
        return "professional"
    if re.search(r"欢迎|很高兴|祝您", text):
        return "friendly"
    if re.search(r"精彩|推荐|值得", text):
        return "excited"
    return "friendly"


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------


def get_llm_client() -> BaseLLMClient:
    """
    根据 LLM_PROVIDER 环境变量返回对应客户端实例。

    - mock   : MockLLMClient（默认）
    - openai : OpenAIClient（OpenAI 兼容）
    """
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        return OpenAIClient()
    return MockLLMClient()


# 向后兼容旧代码中的 LLMService 名称
class LLMService:
    """薄封装，供 ChatService 调用。"""

    def __init__(self) -> None:
        self._client = get_llm_client()

    async def generate(
        self,
        question: str,
        context_chunks: list[dict] | None = None,
        history: list[dict[str, str]] | None = None,
        preference: list[str] | None = None,
    ) -> dict:
        result = await self._client.generate(
            question=question,
            context_chunks=context_chunks or [],
            history=history,
            preference=preference,
        )
        return {
            "answerText": result.answer_text,
            "emotionTag": result.emotion_tag,
            "confidence": result.confidence,
        }
