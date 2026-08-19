"""
基于关键词规则的用户情感分类（轻量级，无额外模型依赖）。

分类结果：positive（正面）| neutral（中性）| negative（负面）
"""

from __future__ import annotations

import re
from typing import Literal

SentimentLabel = Literal["positive", "neutral", "negative"]

POSITIVE_KEYWORDS: tuple[str, ...] = (
    "谢谢",
    "感谢",
    "太好了",
    "很好",
    "不错",
    "喜欢",
    "满意",
    "推荐",
    "漂亮",
    "精彩",
    "有趣",
    "方便",
    "友好",
    "专业",
    "贴心",
    "值得",
    "赞",
    "棒",
    "开心",
    "期待",
    "美好",
    "优美",
    "震撼",
    "感动",
)

NEGATIVE_KEYWORDS: tuple[str, ...] = (
    "不好",
    "差劲",
    "失望",
    "投诉",
    "垃圾",
    "难吃",
    "太贵",
    "坑",
    "骗人",
    "糟糕",
    "差",
    "烂",
    "恶心",
    "生气",
    "愤怒",
    "不满",
    "难找",
    "拥挤",
    "排队",
    "无聊",
    "后悔",
    "不推荐",
    "问题",
    "故障",
    "关闭",
    "骗",
)

NEUTRAL_PATTERNS: tuple[str, ...] = (
    r"^(什么|哪些|哪里|怎么|多少|几点|是否|有没有|能不能)",
    r"(开放时间|门票|价格|地址|路线|交通|停车)",
)


def classify_sentiment(text: str) -> SentimentLabel:
    """
    对用户输入文本进行情感分类。

    规则：
    1. 统计正/负面关键词命中数
    2. 纯信息咨询类问句倾向中性
    3. 正面 > 负面 → positive；反之 negative；相等或无命中 → neutral
    """
    if not text or not text.strip():
        return "neutral"

    normalized = text.strip().lower()

    pos_score = sum(1 for kw in POSITIVE_KEYWORDS if kw in normalized)
    neg_score = sum(1 for kw in NEGATIVE_KEYWORDS if kw in normalized)

    is_inquiry = any(re.search(p, normalized) for p in NEUTRAL_PATTERNS)
    if is_inquiry and pos_score == 0 and neg_score == 0:
        return "neutral"

    if pos_score > neg_score:
        return "positive"
    if neg_score > pos_score:
        return "negative"
    return "neutral"


def sentiment_label_zh(label: SentimentLabel) -> str:
    """英文标签转中文展示名。"""
    return {"positive": "正面", "neutral": "中性", "negative": "负面"}[label]
