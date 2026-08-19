"""
会话记忆服务。

按 sessionId 保存最近 N 轮对话（user + assistant），供 LLM 多轮上下文使用。
优先使用 Redis；连接失败时自动降级为进程内 dict，保证开发环境可用。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionMemoryService:
    """
    会话记忆管理。

    Redis Key 格式: chat:session:{sessionId}
    Value: JSON 数组 [{"role":"user"|"assistant","content":"..."}]
    最多保留 max_turns 轮（每轮 2 条消息）。
    """

    KEY_PREFIX = "chat:session:"

    def __init__(self) -> None:
        self.max_turns = settings.SESSION_MEMORY_MAX_TURNS
        self.ttl = settings.SESSION_MEMORY_TTL
        self._memory: dict[str, list[dict[str, str]]] = {}
        self._redis: aioredis.Redis | None = None
        self._redis_available: bool | None = None

    async def _get_redis(self) -> aioredis.Redis | None:
        """尝试连接 Redis，失败则标记不可用并降级到内存。"""
        if not settings.USE_REDIS_SESSION:
            return None

        if self._redis_available is False:
            return None

        if self._redis is None:
            try:
                client = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await client.ping()
                self._redis = client
                self._redis_available = True
                logger.info("会话记忆：已连接 Redis")
            except Exception as exc:
                logger.warning("会话记忆：Redis 不可用，降级为内存存储 (%s)", exc)
                self._redis_available = False
                return None

        return self._redis

    def _key(self, session_id: str) -> str:
        return f"{self.KEY_PREFIX}{session_id}"

    async def get_history(self, session_id: str) -> list[dict[str, str]]:
        """读取指定会话的最近对话历史。"""
        redis = await self._get_redis()
        if redis:
            raw = await redis.get(self._key(session_id))
            if raw:
                return json.loads(raw)
            return []

        return list(self._memory.get(session_id, []))

    async def append_turn(
        self,
        session_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        """
        追加一轮对话并裁剪至 max_turns。

        一轮 = 1 条 user + 1 条 assistant，共 2 条消息。
        """
        history = await self.get_history(session_id)
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": assistant_text})

        max_messages = self.max_turns * 2
        if len(history) > max_messages:
            history = history[-max_messages:]

        redis = await self._get_redis()
        if redis:
            await redis.set(
                self._key(session_id),
                json.dumps(history, ensure_ascii=False),
                ex=self.ttl,
            )
        else:
            self._memory[session_id] = history

    async def clear(self, session_id: str) -> None:
        """清空指定会话记忆。"""
        redis = await self._get_redis()
        if redis:
            await redis.delete(self._key(session_id))
        self._memory.pop(session_id, None)


# 进程级单例，避免重复创建 Redis 连接
session_memory = SessionMemoryService()
