from pydantic import BaseModel, Field


class SentimentTrendItem(BaseModel):
    date: str
    positive: float = Field(description="正面比例 0~1")
    neutral: float = Field(description="中性比例 0~1")
    negative: float = Field(description="负面比例 0~1")
    total: int = Field(description="当日会话条数")


class HotTopicWord(BaseModel):
    word: str
    count: int
    weight: float = Field(description="词云权重 0~100")


class SentimentSummary(BaseModel):
    totalMessages: int
    positiveRate: float
    neutralRate: float
    negativeRate: float


class SentimentTrendData(BaseModel):
    trend: list[SentimentTrendItem]
    hotTopics: list[HotTopicWord]
    summary: SentimentSummary
