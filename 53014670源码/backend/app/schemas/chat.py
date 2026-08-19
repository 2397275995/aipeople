from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None


class PhonemeItem(BaseModel):
    phone: str
    startMs: int
    endMs: int


class SourceItem(BaseModel):
    docId: str
    title: str
    snippet: str


class TtsPayload(BaseModel):
    audioUrl: str
    durationMs: int
    phonemes: list[PhonemeItem] = Field(default_factory=list)


class AvatarPayload(BaseModel):
    expression: str = "smile"
    gesture: str = "explain"


class ChatAskRequest(BaseModel):
    sessionId: str = Field(..., examples=["sess_abc123"])
    text: str = Field(..., min_length=1, examples=["这个景区有什么历史故事？"])
    inputType: Literal["voice", "text"] = "text"
    preference: list[str] | None = Field(default=None, examples=[["history", "culture"]])
    poiId: str | None = Field(default=None, examples=["poi_001"])


class ChatAskData(BaseModel):
    messageId: str
    answerText: str
    emotionTag: str
    confidence: float
    sources: list[SourceItem] = Field(default_factory=list)
    tts: TtsPayload
    avatar: AvatarPayload


class AsrRecognizeData(BaseModel):
    text: str
    confidence: float
    durationMs: int


class AvatarConfigData(BaseModel):
    avatarId: str
    modelUrl: str
    appearance: dict[str, Any]
    voice: dict[str, Any]
    greeting: dict[str, str]


class SessionLogRequest(BaseModel):
    sessionId: str
    messageId: str
    userText: str
    botText: str
    inputType: str = "text"
    emotionDetected: str | None = None
    emotionResponse: str | None = None
    confidence: float | None = None
    latencyMs: int | None = None
    timestamp: str | None = None
