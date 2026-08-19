"""
管理后台 — 感受度分析 API。

GET /api/v1/admin/analytics/sentiment-trend
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from app.core.deps import DbSession, get_current_admin
from app.schemas.analytics import SentimentTrendData
from app.schemas.chat import ApiResponse
from app.services.analytics_service import AnalyticsService
from app.utils.response import success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])

_analytics = AnalyticsService()


@router.get("/sentiment-trend", response_model=ApiResponse[SentimentTrendData])
async def sentiment_trend(
    db: DbSession,
    days: int = Query(default=7, ge=1, le=30, description="统计天数"),
    _admin: str = Depends(get_current_admin),
) -> ApiResponse[SentimentTrendData]:
    """
    近 N 日用户情感比例趋势 + 热点话题词云数据。

    - trend: 每日 positive/neutral/negative 比例（0~1）及消息总数
    - hotTopics: 用户提问高频词（供词云展示）
    - summary: 周期内整体情感占比汇总
    """
    data = await _analytics.get_sentiment_trend(db, days=days)
    logger.info(
        "sentiment-trend days=%d total_messages=%d topics=%d",
        days,
        data.summary.totalMessages,
        len(data.hotTopics),
    )
    return success(data, message="情感趋势数据获取成功")
