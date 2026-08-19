"""
数据大屏与感受度分析统计服务。
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import ChatMessage, ChatSession
from app.schemas.admin import (
    DashboardOverviewData,
    HotQAItem,
    SatisfactionTrendItem,
)
from app.schemas.analytics import HotTopicWord, SentimentSummary, SentimentTrendData, SentimentTrendItem

logger = logging.getLogger(__name__)

# 景区领域高频词（命中额外加权）
DOMAIN_KEYWORDS: tuple[str, ...] = (
    "灵山",
    "大佛",
    "梵宫",
    "拈花",
    "九龙灌浴",
    "祥符禅寺",
    "五印坛城",
    "门票",
    "开放时间",
    "路线",
    "推荐",
    "历史",
    "文化",
    "禅意",
    "自然",
    "停车",
    "交通",
    "导游",
    "景点",
    "游览",
    "讲解",
    "拈花湾",
    "鹿鸣谷",
    "香月花街",
)

STOPWORDS: frozenset[str] = frozenset(
    {
        "什么",
        "怎么",
        "哪里",
        "哪些",
        "是否",
        "有没有",
        "能不能",
        "可以",
        "请问",
        "一下",
        "知道",
        "告诉",
        "介绍",
        "关于",
        "景区",
        "我们",
        "你们",
        "这个",
        "那个",
        "如何",
        "为什么",
        "多少",
        "几个",
    }
)


class AnalyticsService:
    """运营数据统计。"""

    async def get_dashboard_overview(self, db: AsyncSession) -> DashboardOverviewData:
        """聚合大屏所需全部指标。"""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        session_count = await self._count_today_sessions(db, today_start)
        message_count = await self._count_today_messages(db, today_start)
        hot_qa = await self._top_questions(db, limit=5)
        satisfaction_trend = self._mock_satisfaction_trend(days=7, end_date=now.date())
        avg_satisfaction = round(
            sum(d.avgSatisfaction for d in satisfaction_trend) / len(satisfaction_trend),
            2,
        )

        sentiment_data = await self.get_sentiment_trend(db, days=7)

        logger.info(
            "dashboard overview sessions=%d messages=%d hot_qa=%d",
            session_count,
            message_count,
            len(hot_qa),
        )

        return DashboardOverviewData(
            sessionCount=session_count,
            messageCount=message_count,
            visitorCount=session_count,
            avgSatisfaction=avg_satisfaction,
            hotQA=[item.model_dump() for item in hot_qa],
            satisfactionTrend=[item.model_dump() for item in satisfaction_trend],
            sentimentTrend=[item.model_dump() for item in sentiment_data.trend],
        )

    async def get_sentiment_trend(
        self,
        db: AsyncSession,
        days: int = 7,
    ) -> SentimentTrendData:
        """近 N 日情感比例趋势 + 热点话题词云数据。"""
        now = datetime.now()
        end_date = now.date()
        trend: list[SentimentTrendItem] = []

        for i in range(days - 1, -1, -1):
            day = end_date - timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time())
            day_end = day_start + timedelta(days=1)
            item = await self._sentiment_for_day(db, day_start, day_end, day.isoformat())
            trend.append(item)

        period_start = datetime.combine(end_date - timedelta(days=days - 1), datetime.min.time())
        hot_topics = await self._extract_hot_topics(db, period_start, now)
        summary = self._build_summary(trend)

        return SentimentTrendData(trend=trend, hotTopics=hot_topics, summary=summary)

    @staticmethod
    async def _sentiment_for_day(
        db: AsyncSession,
        day_start: datetime,
        day_end: datetime,
        date_str: str,
    ) -> SentimentTrendItem:
        stmt = (
            select(ChatMessage.sentiment, func.count())
            .where(
                ChatMessage.created_at >= day_start,
                ChatMessage.created_at < day_end,
            )
            .group_by(ChatMessage.sentiment)
        )
        result = await db.execute(stmt)
        rows = result.all()

        counts = {"positive": 0, "neutral": 0, "negative": 0}
        for sentiment, cnt in rows:
            key = sentiment if sentiment in counts else "neutral"
            counts[key] += int(cnt)

        total = sum(counts.values())
        if total == 0:
            return SentimentTrendItem(
                date=date_str,
                positive=0.0,
                neutral=0.0,
                negative=0.0,
                total=0,
            )

        return SentimentTrendItem(
            date=date_str,
            positive=round(counts["positive"] / total, 4),
            neutral=round(counts["neutral"] / total, 4),
            negative=round(counts["negative"] / total, 4),
            total=total,
        )

    @staticmethod
    async def _extract_hot_topics(
        db: AsyncSession,
        start: datetime,
        end: datetime,
        limit: int = 40,
    ) -> list[HotTopicWord]:
        stmt = select(ChatMessage.user_text).where(
            ChatMessage.created_at >= start,
            ChatMessage.created_at <= end,
        )
        result = await db.execute(stmt)
        texts = [row[0] for row in result.all() if row[0]]

        counter: Counter[str] = Counter()
        for text in texts:
            for word in re.findall(r"[\u4e00-\u9fff]{2,4}", text):
                if word in STOPWORDS:
                    continue
                counter[word] += 1
            for kw in DOMAIN_KEYWORDS:
                if kw in text:
                    counter[kw] += 2

        if not counter:
            return [
                HotTopicWord(word=kw, count=1, weight=50.0)
                for kw in DOMAIN_KEYWORDS[:10]
            ]

        top = counter.most_common(limit)
        max_count = top[0][1]
        return [
            HotTopicWord(
                word=word,
                count=count,
                weight=round(count / max_count * 100, 1),
            )
            for word, count in top
        ]

    @staticmethod
    def _build_summary(trend: list[SentimentTrendItem]) -> SentimentSummary:
        total = sum(item.total for item in trend)
        if total == 0:
            return SentimentSummary(
                totalMessages=0,
                positiveRate=0.0,
                neutralRate=0.0,
                negativeRate=0.0,
            )

        pos = sum(item.positive * item.total for item in trend)
        neu = sum(item.neutral * item.total for item in trend)
        neg = sum(item.negative * item.total for item in trend)

        return SentimentSummary(
            totalMessages=total,
            positiveRate=round(pos / total, 4),
            neutralRate=round(neu / total, 4),
            negativeRate=round(neg / total, 4),
        )

    @staticmethod
    async def _count_today_sessions(db: AsyncSession, today_start: datetime) -> int:
        """今日有问答行为的独立 session 数。"""
        stmt = select(func.count(func.distinct(ChatMessage.session_id))).where(
            ChatMessage.created_at >= today_start
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0
        if count > 0:
            return int(count)

        stmt2 = select(func.count()).select_from(ChatSession).where(
            ChatSession.updated_at >= today_start
        )
        result2 = await db.execute(stmt2)
        return int(result2.scalar() or 0)

    @staticmethod
    async def _count_today_messages(db: AsyncSession, today_start: datetime) -> int:
        stmt = select(func.count()).select_from(ChatMessage).where(
            ChatMessage.created_at >= today_start
        )
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    @staticmethod
    async def _top_questions(db: AsyncSession, limit: int = 5) -> list[HotQAItem]:
        """按 user_text 分组统计 TOP N 热门问题。"""
        stmt = (
            select(ChatMessage.user_text, func.count().label("cnt"))
            .group_by(ChatMessage.user_text)
            .order_by(desc("cnt"))
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [
            HotQAItem(question=str(text)[:200], count=int(cnt))
            for text, cnt in rows
        ]

    @staticmethod
    def _mock_satisfaction_trend(days: int, end_date) -> list[SatisfactionTrendItem]:
        """
        近 N 日满意度 mock（3.6 ~ 4.9 分，按日期确定性随机）。

        后续可替换为真实用户评分表聚合。
        """
        items: list[SatisfactionTrendItem] = []
        for i in range(days - 1, -1, -1):
            day = end_date - timedelta(days=i)
            seed = hashlib.md5(day.isoformat().encode()).hexdigest()
            value = 3.6 + (int(seed[:4], 16) % 14) / 10.0
            items.append(
                SatisfactionTrendItem(
                    date=day.isoformat(),
                    avgSatisfaction=round(value, 2),
                )
            )
        return items
