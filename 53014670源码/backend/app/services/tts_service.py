"""
TTS 语音合成服务（Edge-TTS）。

使用微软 Edge TTS 免费接口合成语音，并从 WordBoundary 事件提取
时间戳用于前端 Live2D 口型同步（ParamMouthOpenY）。

音频文件缓存至 TTS_OUTPUT_DIR，通过 /static/tts/ 对外提供 URL。
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from pathlib import Path

import edge_tts

from app.core.config import settings
from app.schemas.chat import PhonemeItem, TtsPayload
from app.utils import generate_id

logger = logging.getLogger(__name__)

# Edge-TTS 音色映射（配置项 TTS_VOICE 可使用别名或完整 Neural 名称）
VOICE_ALIASES: dict[str, str] = {
    "zh_female_warm": "zh-CN-XiaoxiaoNeural",
    "zh_female": "zh-CN-XiaoxiaoNeural",
    "zh_male": "zh-CN-YunxiNeural",
    "zh_male_warm": "zh-CN-YunxiNeural",
}


class TTSService:
    """Edge-TTS 语音合成服务。"""

    def __init__(self) -> None:
        self.output_dir = Path(settings.TTS_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_voice(self, voice: str | None = None) -> str:
        name = voice or settings.TTS_VOICE
        return VOICE_ALIASES.get(name, name)

    def _build_audio_url(self, filename: str) -> str:
        base = settings.TTS_PUBLIC_BASE_URL.rstrip("/")
        return f"{base}/static/tts/{filename}"

    async def synthesize(
        self,
        text: str,
        message_id: str | None = None,
        *,
        voice: str | None = None,
    ) -> TtsPayload:
        """
        合成语音并生成口型时间戳（供 chat/ask 调用）。

        Returns:
            TtsPayload(audioUrl, durationMs, phonemes)
        """
        text = text.strip()
        if not text:
            raise ValueError("TTS 文本不能为空")

        msg_id = message_id or generate_id("msg")
        filename = f"{msg_id}.mp3"
        output_path = self.output_dir / filename
        edge_voice = self._resolve_voice(voice)

        _audio_bytes, phonemes = await self._synthesize_edge(
            text=text,
            voice=edge_voice,
            output_path=output_path,
        )

        duration_ms = phonemes[-1].endMs + 100 if phonemes else _estimate_duration(text)

        logger.info(
            "TTS 合成完成: msg=%s voice=%s duration=%dms phonemes=%d",
            msg_id,
            edge_voice,
            duration_ms,
            len(phonemes),
        )

        return TtsPayload(
            audioUrl=self._build_audio_url(filename),
            durationMs=duration_ms,
            phonemes=phonemes,
        )

    async def synthesize_with_base64(
        self,
        text: str,
        message_id: str | None = None,
        *,
        voice: str | None = None,
    ) -> dict:
        """合成并返回含 audioBase64 的完整字典（供 /tts/synthesize 使用）。"""
        msg_id = message_id or generate_id("msg")
        filename = f"{msg_id}.mp3"
        output_path = self.output_dir / filename
        edge_voice = self._resolve_voice(voice)

        audio_bytes, phonemes = await self._synthesize_edge(
            text=text,
            voice=edge_voice,
            output_path=output_path,
        )
        duration_ms = phonemes[-1].endMs + 100 if phonemes else _estimate_duration(text)

        return {
            "audioUrl": self._build_audio_url(filename),
            "audioBase64": base64.b64encode(audio_bytes).decode("ascii"),
            "durationMs": duration_ms,
            "phonemes": phonemes,
        }

    async def _synthesize_edge(
        self,
        text: str,
        voice: str,
        output_path: Path,
    ) -> tuple[bytes, list[PhonemeItem]]:
        """
        调用 edge-tts 流式合成。

        从 WordBoundary 事件提取时间戳；若无边界事件则按字符均分时长。
        """
        communicate = edge_tts.Communicate(
            text,
            voice=voice,
            rate=settings.TTS_RATE,
            volume=settings.TTS_VOLUME,
        )

        audio_chunks: list[bytes] = []
        phonemes: list[PhonemeItem] = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset / duration 单位为 100 纳秒
                start_ms = int(chunk["offset"] / 10_000)
                end_ms = start_ms + int(chunk["duration"] / 10_000)
                phone_text = chunk["text"].strip()
                if phone_text:
                    phonemes.append(
                        PhonemeItem(phone=phone_text, startMs=start_ms, endMs=end_ms)
                    )

        audio_bytes = b"".join(audio_chunks)
        if not audio_bytes:
            raise RuntimeError("Edge-TTS 未返回音频数据，请检查网络或音色配置")

        # 写入本地缓存
        await asyncio.to_thread(output_path.write_bytes, audio_bytes)

        # 无 WordBoundary 时回退：按可见字符均分
        if not phonemes:
            duration_ms = _estimate_duration(text)
            phonemes = _estimate_phonemes_by_char(text, duration_ms)
            logger.warning("Edge-TTS 未返回 WordBoundary，使用字符均分口型时间戳")

        return audio_bytes, phonemes


def _estimate_duration(text: str) -> int:
    """按中文语速估算时长（约 4 字/秒）。"""
    visible = len(re.sub(r"\s+", "", text))
    return max(1000, int(visible / 4.0 * 1000))


def _estimate_phonemes_by_char(text: str, duration_ms: int) -> list[PhonemeItem]:
    """将文本按字符均分时间段，生成口型驱动序列。"""
    chars = [c for c in text if c.strip()]
    if not chars:
        return [PhonemeItem(phone="sil", startMs=0, endMs=duration_ms)]

    slice_ms = max(50, duration_ms // len(chars))
    phonemes: list[PhonemeItem] = []
    for i, ch in enumerate(chars):
        start = i * slice_ms
        end = min((i + 1) * slice_ms, duration_ms)
        phonemes.append(PhonemeItem(phone=ch, startMs=start, endMs=end))
    return phonemes
