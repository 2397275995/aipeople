"""
ASR 语音识别服务。

提供两种可切换实现：
  - FasterWhisperASR : 本地 faster-whisper（默认，离线可用，small 模型）
  - OpenAIWhisperASR : OpenAI Whisper API（需 API Key）

通过环境变量 ASR_PROVIDER=faster-whisper|openai 切换。
"""

from __future__ import annotations

import asyncio
import io
import logging
import tempfile
import wave
from abc import ABC, abstractmethod
from pathlib import Path

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 自定义异常
# ---------------------------------------------------------------------------


class ASRError(Exception):
    """ASR 基础异常。"""


class ASRInvalidAudioError(ASRError):
    """音频格式无效或无法解析。"""


class ASRTooShortError(ASRError):
    """录音时长过短。"""


class ASREmptyResultError(ASRError):
    """识别结果为空。"""


# ---------------------------------------------------------------------------
# 音频工具
# ---------------------------------------------------------------------------


def parse_wav_duration_ms(audio_bytes: bytes) -> int:
    """
    从 WAV 文件头解析时长（毫秒）。

    支持标准 PCM WAV；解析失败时抛出 ASRInvalidAudioError。
    """
    if len(audio_bytes) < 44:
        raise ASRInvalidAudioError("音频文件过小或格式不正确")

    if audio_bytes[:4] != b"RIFF" or audio_bytes[8:12] != b"WAVE":
        raise ASRInvalidAudioError("仅支持 WAV 格式音频，请检查前端录音编码")

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate <= 0:
                raise ASRInvalidAudioError("无效的采样率")
            return int(frames / rate * 1000)
    except wave.Error as exc:
        raise ASRInvalidAudioError(f"WAV 解析失败: {exc}") from exc


def validate_audio(audio_bytes: bytes) -> int:
    """
    校验音频大小与时长。

    Returns:
        duration_ms
    """
    if not audio_bytes:
        raise ASRInvalidAudioError("音频文件为空")

    if len(audio_bytes) > settings.ASR_MAX_FILE_SIZE:
        raise ASRInvalidAudioError(
            f"音频文件过大（最大 {settings.ASR_MAX_FILE_SIZE // 1024 // 1024}MB）"
        )

    duration_ms = parse_wav_duration_ms(audio_bytes)
    if duration_ms < settings.ASR_MIN_DURATION_MS:
        raise ASRTooShortError(
            f"录音时长过短（{duration_ms}ms），请至少录制 {settings.ASR_MIN_DURATION_MS}ms"
        )
    return duration_ms


def logprob_to_confidence(avg_logprob: float) -> float:
    """
    将 Whisper avg_logprob（负数）映射到 [0.1, 0.99] 置信度。
    """
    # avg_logprob 通常在 [-1.0, 0.0] 区间
    score = 1.0 + avg_logprob
    return round(max(0.1, min(0.99, score)), 2)


# ---------------------------------------------------------------------------
# 抽象接口
# ---------------------------------------------------------------------------


class BaseASRClient(ABC):
    """ASR 客户端抽象接口。"""

    @abstractmethod
    def transcribe_sync(self, audio_bytes: bytes, lang: str = "zh") -> dict:
        """
        同步转写音频。

        Returns:
            {"text": str, "confidence": float, "durationMs": int}
        """
        ...


# ---------------------------------------------------------------------------
# HuggingFace 下载环境（避免系统代理导致 SSL 失败）
# ---------------------------------------------------------------------------


def _configure_hf_download_env() -> None:
    """加载 faster-whisper 前配置 HuggingFace 下载环境。"""
    import os

    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        os.environ.pop(key, None)
    os.environ.setdefault("NO_PROXY", "*")
    if settings.ASR_HF_ENDPOINT:
        os.environ.setdefault("HF_ENDPOINT", settings.ASR_HF_ENDPOINT)


# ---------------------------------------------------------------------------
# faster-whisper 本地实现（默认）
# ---------------------------------------------------------------------------


class FasterWhisperASR(BaseASRClient):
    """
    基于 faster-whisper 的本地离线 ASR。

    默认加载 small 模型，首次运行会自动下载模型权重。
    CPU 环境建议使用 compute_type=int8 以降低内存占用。
    """

    _model = None
    _model_lock = asyncio.Lock()

    @classmethod
    def _load_model(cls):
        if cls._model is None:
            _configure_hf_download_env()
            from faster_whisper import WhisperModel

            model_id = settings.ASR_MODEL_PATH.strip() or settings.ASR_MODEL
            logger.info(
                "加载 faster-whisper 模型: %s (device=%s, compute_type=%s)",
                model_id,
                settings.ASR_DEVICE,
                settings.ASR_COMPUTE_TYPE,
            )
            try:
                cls._model = WhisperModel(
                    model_id,
                    device=settings.ASR_DEVICE,
                    compute_type=settings.ASR_COMPUTE_TYPE,
                )
            except Exception as exc:
                logger.error("faster-whisper 模型加载失败: %s", exc)
                raise ASRError(
                    "语音识别模型加载失败。若首次使用需联网下载，请检查网络/代理；"
                    "或设置 ASR_MODEL_PATH 指向已下载的本地模型目录。"
                ) from exc
        return cls._model

    def transcribe_sync(self, audio_bytes: bytes, lang: str = "zh") -> dict:
        duration_ms = validate_audio(audio_bytes)
        model = self._load_model()

        # faster-whisper 需要文件路径；写入临时 WAV
        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            language = "zh" if lang in ("zh", "zh-CN", "cn") else lang
            segments, info = model.transcribe(
                tmp_path,
                language=language,
                beam_size=5,
                vad_filter=True,
            )

            segment_list = list(segments)
            text = "".join(seg.text for seg in segment_list).strip()

            if not text:
                raise ASREmptyResultError("未识别到有效语音内容，请靠近麦克风重试")

            if segment_list:
                avg_logprob = sum(s.avg_logprob for s in segment_list) / len(segment_list)
                confidence = logprob_to_confidence(avg_logprob)
            else:
                confidence = 0.5

            logger.info(
                "faster-whisper 识别完成: lang=%s duration=%dms text=%r confidence=%.2f",
                info.language,
                duration_ms,
                text[:50],
                confidence,
            )

            return {
                "text": text,
                "confidence": confidence,
                "durationMs": duration_ms,
            }
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# OpenAI Whisper API 实现
# ---------------------------------------------------------------------------


class OpenAIWhisperASR(BaseASRClient):
    """
    OpenAI Audio Transcriptions API（/v1/audio/transcriptions）。

    也可用于兼容 OpenAI 接口的第三方服务（配置 ASR_API_BASE）。
    """

    def transcribe_sync(self, audio_bytes: bytes, lang: str = "zh") -> dict:
        duration_ms = validate_audio(audio_bytes)

        api_key = settings.ASR_API_KEY or settings.LLM_API_KEY
        if not api_key:
            raise ASRError("ASR_API_KEY 未配置，无法调用 OpenAI Whisper API")

        api_base = (settings.ASR_API_BASE or settings.LLM_API_BASE).rstrip("/")
        model = settings.ASR_OPENAI_MODEL

        language = "zh" if lang in ("zh", "zh-CN", "cn") else lang

        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data = {"model": model, "language": language, "response_format": "json"}

        with httpx.Client(timeout=settings.ASR_TIMEOUT, trust_env=False) as client:
            resp = client.post(
                f"{api_base}/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files=files,
                data=data,
            )
            resp.raise_for_status()
            result = resp.json()

        text = (result.get("text") or "").strip()
        if not text:
            raise ASREmptyResultError("未识别到有效语音内容")

        # OpenAI 不返回置信度，根据文本长度给出估算值
        confidence = 0.92 if len(text) >= 4 else 0.75

        return {
            "text": text,
            "confidence": confidence,
            "durationMs": duration_ms,
        }


# ---------------------------------------------------------------------------
# 工厂 & 服务门面
# ---------------------------------------------------------------------------


def get_asr_client() -> BaseASRClient:
    """
    根据 ASR_PROVIDER 返回 ASR 客户端。

    - faster-whisper : 本地 faster-whisper（默认）
    - openai         : OpenAI Whisper API
    """
    provider = settings.ASR_PROVIDER.lower()
    if provider == "openai":
        return OpenAIWhisperASR()
    return FasterWhisperASR()


class ASRService:
    """ASR 服务门面，供 API 路由调用。"""

    def __init__(self) -> None:
        self._client = get_asr_client()

    async def recognize(self, audio_bytes: bytes, lang: str = "zh") -> dict:
        """
        异步语音识别。

        转写为 CPU/GPU 密集型操作，通过 asyncio.to_thread 避免阻塞事件循环。
        """
        return await asyncio.to_thread(
            self._client.transcribe_sync,
            audio_bytes,
            lang,
        )
