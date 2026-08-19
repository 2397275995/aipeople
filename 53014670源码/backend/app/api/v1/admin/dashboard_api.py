"""
管理后台 — 数据大屏 API。

GET /api/v1/admin/dashboard/overview
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, get_current_admin
from app.schemas.admin import DashboardOverviewData
from app.schemas.chat import ApiResponse
from app.services.analytics_service import AnalyticsService
from app.utils.response import success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

_analytics = AnalyticsService()


@router.get("/dashboard/overview", response_model=ApiResponse[DashboardOverviewData])
async def dashboard_overview(
    db: DbSession,
    period: str = "today",
    _admin: str = Depends(get_current_admin),
) -> ApiResponse[DashboardOverviewData]:
    """
    数据大屏概览。

    - sessionCount: 今日服务人次（独立 session 数）
    - hotQA: 热门 TOP5 问题
    - satisfactionTrend: 近 7 日平均满意度（当前 mock）
    """
    _ = period
    data = await _analytics.get_dashboard_overview(db)
    return success(data)
