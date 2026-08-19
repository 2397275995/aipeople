"""TTS 相关 Schema。"""

from pydantic import BaseModel, Field

from app.schemas.chat import PhonemeItem, TtsPayload


class TtsSynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="待合成文本")
    messageId: str | None = Field(default=None, description="可选消息 ID，用于文件命名")
    voice: str | None = Field(default=None, description="音色，默认读取 TTS_VOICE 配置")
    returnBase64: bool = Field(default=False, description="是否同时返回 base64 音频")


class TtsSynthesizeData(BaseModel):
    audioUrl: str
    audioBase64: str | None = None
    durationMs: int
    phonemes: list[PhonemeItem] = Field(default_factory=list)


# 复用 chat 中的 TtsPayload 作为 chat/ask 内嵌结构
__all__ = ["TtsSynthesizeRequest", "TtsSynthesizeData", "TtsPayload", "PhonemeItem"]
