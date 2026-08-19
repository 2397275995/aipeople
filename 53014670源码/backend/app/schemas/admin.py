from typing import Any

from pydantic import BaseModel, Field

from app.schemas.recommend import RecommendRoutesData, RouteItem

__all__ = ["RouteItem", "RecommendRoutesData"]


class HotQAItem(BaseModel):
    question: str
    count: int


class SatisfactionTrendItem(BaseModel):
    date: str
    avgSatisfaction: float


class DashboardOverviewData(BaseModel):
    sessionCount: int
    messageCount: int = 0
    visitorCount: int = 0
    avgSatisfaction: float
    hotQA: list[dict[str, Any]]
    satisfactionTrend: list[dict[str, Any]] = Field(default_factory=list)
    sentimentTrend: list[dict[str, Any]] = Field(default_factory=list)


class KbDocumentUploadData(BaseModel):
    docId: str
    status: str
    chunkCount: int
    progress: int = 0


class KbDocumentItem(BaseModel):
    docId: str
    title: str
    filename: str
    category: str
    scenicAreaId: str
    status: str
    progress: int
    chunkCount: int
    createdAt: str
    errorMessage: str | None = None


class KbDocumentListData(BaseModel):
    documents: list[KbDocumentItem]


class KbDocumentStatusData(BaseModel):
    docId: str
    status: str
    progress: int
    chunkCount: int
    errorMessage: str | None = None


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginData(BaseModel):
    token: str
    tokenType: str = "Bearer"
    expiresIn: int
