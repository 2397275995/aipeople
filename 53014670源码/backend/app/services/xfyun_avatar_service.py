from __future__ import annotations

import base64
import json
import logging
import uuid
from datetime import datetime
from hashlib import sha256
from hmac import new as hmac_new
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _truncate_utf8(text: str, max_bytes: int) -> str:
    result = ""
    used = 0
    for char in text.strip():
        char_bytes = len(char.encode("utf-8"))
        if used + char_bytes > max_bytes:
            break
        result += char
        used += char_bytes
    return result


def _build_auth_url(url: str, method: str = "POST") -> tuple[str, dict[str, str]]:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path or "/"
    date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    signature_origin = f"host: {host}\ndate: {date}\n{method} {path} HTTP/1.1"
    logger.debug("[XFYunAvatar] signature_origin=%s", repr(signature_origin))
    signature = base64.b64encode(
        hmac_new(settings.XFYUN_API_SECRET.encode(), signature_origin.encode(), sha256).digest()
    ).decode()
    auth_origin = (
        f'api_key="{settings.XFYUN_API_KEY}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(auth_origin.encode()).decode()
    auth_url = f"{url}?authorization={quote(authorization)}&date={quote(date)}&host={quote(host)}"
    headers = {
        "Host": host,
        "Date": date,
        "Authorization": authorization,
        "Content-Type": "application/json",
    }
    return auth_url, headers


class XFYunOnlineAvatarSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._session = None
        self._stream_url = None
        self._client = httpx.Client(timeout=30)

    async def start(self) -> str:
        url, headers = _build_auth_url("https://vms.cn-huadong-1.xf-yun.com/v1/private/vms2d_start")
        
        body = {
            "header": {
                "app_id": settings.XFYUN_APP_ID,
                "uid": "",
            },
            "parameter": {
                "vmr": {
                    "stream": {
                        "protocol": "xrtc",
                    },
                    "avatar_id": settings.XFYUN_AVATAR_ID,
                    "width": 720,
                    "height": 405,
                },
            },
        }
        
        if settings.XFYUN_SCENE_ID:
            body["parameter"]["vmr"]["scene_id"] = settings.XFYUN_SCENE_ID
        
        try:
            logger.info("[XFYunOnlineAvatar:%s] 启动请求: url=%s, body=%s", self.session_id, url, json.dumps(body))
            resp = self._client.post(url, json=body, headers=headers)
            logger.info("[XFYunOnlineAvatar:%s] 响应状态: %d", self.session_id, resp.status_code)
            
            try:
                data = resp.json()
                logger.info("[XFYunOnlineAvatar:%s] 响应数据: %s", self.session_id, json.dumps(data))
            except Exception:
                logger.info("[XFYunOnlineAvatar:%s] 响应文本: %s", self.session_id, resp.text[:500])
            
            if resp.status_code == 500:
                data = resp.json()
                code = data.get("header", {}).get("code", 0)
                if code == 20015:
                    raise RuntimeError(f"形象ID {settings.XFYUN_AVATAR_ID} 无效，请确认服务类型")
                if code == 11203:
                    raise RuntimeError(f"服务未开通或权限不足，请确认已开通AI虚拟人技术服务")
            
            resp.raise_for_status()
            data = resp.json()
            header = data.get("header") or {}
            if header.get("code", 0) != 0:
                raise RuntimeError(f"启动失败: code={header.get('code')}, message={header.get('message')}")
            payload = data.get("payload") or {}
            self._session = payload.get("session")
            self._stream_url = payload.get("stream_url")
            if not self._stream_url:
                raise RuntimeError("未获取到流地址")
            logger.info("[XFYunOnlineAvatar:%s] 启动成功, stream_url=%s", self.session_id, self._stream_url)
            return self._stream_url
        except Exception as exc:
            logger.error("[XFYunOnlineAvatar:%s] 启动失败: %s", self.session_id, exc)
            raise

    async def talk(self, text: str, mode: str = "interact") -> str | None:
        if not self._session:
            raise RuntimeError("会话未启动")
        url, headers = _build_auth_url("https://vms.cn-huadong-1.xf-yun.com/v1/private/vms2d_ctrl")
        body = {
            "header": {
                "app_id": settings.XFYUN_APP_ID,
                "uid": "",
                "session": self._session,
            },
            "parameter": {
                "tts": {
                    "vcn": settings.XFYUN_VCN or "x4_xiaoxuan",
                    "speed": 50,
                    "pitch": 50,
                    "volume": 50,
                    "rhy": 3,
                },
            },
            "payload": {
                "text": {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "plain",
                    "status": 3,
                    "seq": 0,
                    "text": text,
                },
                "ctrl_w": {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "json",
                    "status": 3,
                    "seq": 0,
                    "text": "",
                },
            },
        }
        try:
            resp = self._client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            header = data.get("header") or {}
            if header.get("code", 0) != 0:
                raise RuntimeError(f"文本驱动失败: code={header.get('code')}, message={header.get('message')}")
            return text
        except Exception as exc:
            logger.error("[XFYunOnlineAvatar:%s] 文本驱动失败: %s", self.session_id, exc)
            raise

    async def stop(self):
        if not self._session:
            return
        url, headers = _build_auth_url("https://vms.cn-huadong-1.xf-yun.com/v1/private/vms2d_stop")
        body = {
            "header": {
                "app_id": settings.XFYUN_APP_ID,
                "request_id": uuid.uuid4().hex,
                "session": self._session,
            },
            "payload": {},
        }
        try:
            resp = self._client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            logger.info("[XFYunOnlineAvatar:%s] 已停止", self.session_id)
        except Exception as exc:
            logger.error("[XFYunOnlineAvatar:%s] 停止失败: %s", self.session_id, exc)
        finally:
            self._session = None
            self._stream_url = None


class XFYunVideoGenClient:
    BASE_URL = "https://vms.cn-huadong-1.xf-yun.com/v1/private"

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30)

    async def generate_video(self, prompt: str, word_count: int = 120) -> dict:
        url = f"{self.BASE_URL}/video/generate"
        auth_url, headers = _build_auth_url(url, "POST")

        safe_prompt = _truncate_utf8(prompt, 280)
        safe_word_count = max(min(int(word_count or 80), 120), 50)

        if not safe_prompt:
            raise RuntimeError("生成视频的文本不能为空")

        body = {
            "header": {
                "app_id": settings.XFYUN_APP_ID,
            },
            "parameter": {
                "avatar": {
                    "prompt": safe_prompt,
                    "word_count": safe_word_count,
                },
            },
        }

        try:
            logger.info(
                "[XFYunVideoGen] 创建视频任务: url=%s, original_prompt_len=%d, safe_prompt_len=%d, safe_prompt_bytes=%d, word_count=%d",
                url,
                len(prompt),
                len(safe_prompt),
                len(safe_prompt.encode("utf-8")),
                safe_word_count,
            )
            resp = await self._client.post(auth_url, json=body, headers=headers)
            logger.info("[XFYunVideoGen] 响应状态: %d", resp.status_code)

            data = resp.json()
            logger.info("[XFYunVideoGen] 响应数据: %s", json.dumps(data, ensure_ascii=False))

            header = data.get("header", {})
            code = header.get("code", 0)

            if resp.status_code >= 400 or code != 0:
                raise RuntimeError(f"创建任务失败: http={resp.status_code}, code={code}, message={header.get('message') or data.get('message')}")

            task_id = header.get("task_id")
            if not task_id:
                raise RuntimeError("未返回task_id")

            return {"task_id": task_id, "task_status": str(header.get("task_status", "1")), "message": header.get("message", "success")}

        except Exception as exc:
            logger.error("[XFYunVideoGen] 创建任务失败: %s", exc)
            raise

    async def query_task(self, task_id: str) -> dict:
        url = f"{self.BASE_URL}/video/query"
        auth_url, headers = _build_auth_url(url, "POST")
        
        body = {
            "header": {
                "app_id": settings.XFYUN_APP_ID,
                "task_id": task_id,
            },
        }
        
        try:
            logger.info("[XFYunVideoGen] 查询任务状态: task_id=%s", task_id)
            resp = await self._client.post(auth_url, json=body, headers=headers)
            logger.info("[XFYunVideoGen] 响应状态: %d", resp.status_code)
            
            data = resp.json()
            logger.info("[XFYunVideoGen] 响应数据: %s", json.dumps(data))
            
            header = data.get("header", {})
            code = header.get("code", 0)
            
            if code != 0:
                raise RuntimeError(f"查询失败: code={code}, message={header.get('message')}")
            
            payload = data.get("payload") or {}
            result = {
                "task_id": header.get("task_id"),
                "task_status": str(header.get("task_status", "")),
                "message": header.get("message"),
                "payload": payload,
            }

            if isinstance(payload, dict):
                result["text"] = payload.get("text") or payload.get("expanded_text") or ""
                result["image_url"] = payload.get("image") or payload.get("image_url") or ""
                result["audio_url"] = payload.get("audio") or payload.get("audio_url") or ""
                result["bgm_url"] = payload.get("bgm") or payload.get("bgm_url") or ""
                result["video_url"] = payload.get("video") or payload.get("video_url") or ""

            return result
            
        except Exception as exc:
            logger.error("[XFYunVideoGen] 查询任务失败: %s", exc)
            raise

    async def generate_and_wait(self, prompt: str, word_count: int = 120, max_wait_seconds: int = 180) -> dict:
        task = await self.generate_video(prompt, word_count)
        task_id = task["task_id"]
        
        import asyncio
        elapsed = 0
        failed_attempts = 0
        max_failed_attempts = 5
        
        while elapsed < max_wait_seconds:
            await asyncio.sleep(3)
            elapsed += 3
            
            try:
                status = await self.query_task(task_id)
                task_status = str(status.get("task_status", ""))
                
                if task_status in ("3", "4"):
                    video_url = status.get("video_url")
                    if video_url:
                        return status
                    payload = status.get("payload", {})
                    if isinstance(payload, dict):
                        video_url = payload.get("video") or payload.get("video_url")
                        if video_url:
                            status["video_url"] = video_url
                            status["text"] = status.get("text") or payload.get("text") or payload.get("expanded_text") or ""
                            return status
                    raise RuntimeError(f"任务已完成但未返回视频地址: {status}")
                elif task_status in ("1", "2"):
                    logger.info("[XFYunVideoGen] 任务处理中: elapsed=%ds, status=%s", elapsed, task_status)
                    failed_attempts = 0
                    continue
                else:
                    failed_attempts += 1
                    if failed_attempts >= max_failed_attempts:
                        raise RuntimeError(f"任务异常: {status}")
                    logger.warning("[XFYunVideoGen] 任务状态异常，重试中: status=%s", task_status)
            except RuntimeError as e:
                failed_attempts += 1
                if failed_attempts >= max_failed_attempts:
                    raise
                logger.warning("[XFYunVideoGen] 查询失败，重试中: %s", e)
        
        raise RuntimeError(f"等待超时，当前状态: {await self.query_task(task_id)}")


class XFYunAvatarManager:
    def __init__(self):
        self._sessions: dict[str, XFYunOnlineAvatarSession] = {}
        self._video_gen_client = XFYunVideoGenClient()

    async def start(self) -> dict[str, str]:
        session_id = uuid.uuid4().hex
        session = XFYunOnlineAvatarSession(session_id)
        try:
            stream_url = await session.start()
            self._sessions[session_id] = session
            return {"sessionId": session_id, "streamUrl": stream_url}
        except RuntimeError as e:
            logger.error("[XFYunAvatarManager] 启动失败: %s", e)
            raise

    async def talk(self, session_id: str, text: str, mode: str = "interact") -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            raise RuntimeError("会话不存在或已过期")
        await session.talk(text, mode)
        return {"reply": text}

    async def stop(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session:
            await session.stop()

    async def generate_video(self, prompt: str, word_count: int = 120) -> dict:
        return await self._video_gen_client.generate_video(prompt, word_count)

    async def query_video_task(self, task_id: str) -> dict:
        return await self._video_gen_client.query_task(task_id)

    async def generate_video_sync(self, prompt: str, word_count: int = 120) -> dict:
        return await self._video_gen_client.generate_and_wait(prompt, word_count)


avatar_manager = XFYunAvatarManager()
video_gen_client = XFYunVideoGenClient()
