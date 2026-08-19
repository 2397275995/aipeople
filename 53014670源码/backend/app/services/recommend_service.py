"""
基于兴趣标签的景区路线推荐服务。

POI 数据来自 JSON 文件，按 preference 标签匹配评分，
生成 2 条路线，每条 3~4 个 POI，并按距离贪心排序。
"""

from __future__ import annotations

import json
import logging
import math
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.schemas.recommend import PoiItem, RouteItem

logger = logging.getLogger(__name__)

# preference 别名映射（支持中文或简写）
PREFERENCE_ALIASES: dict[str, str] = {
    "历史": "history",
    "文化": "culture",
    "自然": "nature",
    "摄影": "photo",
    "亲子": "family",
    "探险": "adventure",
    "hist": "history",
    "nat": "nature",
}

DEFAULT_ROUTES: list[dict] = [
    {
        "routeId": "route_lingshan_classic",
        "name": "灵山胜境朝圣线",
        "description": "沿中轴线游览灵山大照壁、九龙灌浴、灵山大佛、灵山梵宫等核心景点。",
        "poiIds": [],
        "highlights": ["灵山大佛", "灵山梵宫", "九龙灌浴"],
    },
    {
        "routeId": "route_nianhua_town",
        "name": "拈花湾禅意休闲线",
        "description": "漫步拈花广场、梵天花海、香月花街与五灯湖，体验禅意小镇。",
        "poiIds": [],
        "highlights": ["拈花广场", "梵天花海", "五灯湖"],
    },
]

ROUTE_NAME_TEMPLATES: dict[str, str] = {
    "history": "历史文化精选线",
    "culture": "人文艺术体验线",
    "nature": "自然风光漫步线",
    "photo": "摄影打卡专线",
    "family": "亲子休闲欢乐线",
    "adventure": "户外探险挑战线",
}


@lru_cache
def _load_poi_data() -> dict:
    path = Path(settings.SCENIC_POIS_FILE)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    if not path.exists():
        raise FileNotFoundError(f"POI 数据文件不存在: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _normalize_preferences(preferences: list[str]) -> list[str]:
    normalized: list[str] = []
    for pref in preferences:
        key = pref.strip().lower()
        if not key:
            continue
        normalized.append(PREFERENCE_ALIASES.get(key, key))
    return list(dict.fromkeys(normalized))


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """两点球面距离（米）。"""
    r = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _poi_to_item(raw: dict) -> PoiItem:
    return PoiItem(
        id=raw["id"],
        name=raw["name"],
        lat=raw["lat"],
        lng=raw["lng"],
        description=raw["description"],
        tags=raw["tags"],
        visitMinutes=raw.get("visitMinutes", 30),
    )


def _score_poi(poi: dict, preferences: list[str]) -> float:
    if not preferences:
        return 1.0
    tags = set(poi["tags"])
    prefs = set(preferences)
    overlap = len(tags & prefs)
    if overlap == 0:
        return 0.0
    return overlap / len(prefs) + overlap * 0.1


def _order_by_proximity(pois: list[dict]) -> list[dict]:
    """贪心最近邻排序，使路线连贯。"""
    if len(pois) <= 1:
        return pois
    remaining = pois.copy()
    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1]
        nearest_idx = min(
            range(len(remaining)),
            key=lambda i: _haversine_m(last["lat"], last["lng"], remaining[i]["lat"], remaining[i]["lng"]),
        )
        ordered.append(remaining.pop(nearest_idx))
    return ordered


def _estimate_duration(pois: list[dict]) -> int:
    """游览 + 步行时间（分钟）。"""
    visit = sum(p.get("visitMinutes", 30) for p in pois)
    walk = 0
    for i in range(len(pois) - 1):
        dist = _haversine_m(pois[i]["lat"], pois[i]["lng"], pois[i + 1]["lat"], pois[i + 1]["lng"])
        walk += dist / 80  # 约 80 米/分钟步行
    return int(visit + walk)


def _build_route(
    route_id: str,
    name: str,
    description: str,
    poi_dicts: list[dict],
    match_score: float,
) -> RouteItem:
    ordered = _order_by_proximity(poi_dicts)
    items = [_poi_to_item(p) for p in ordered]
    return RouteItem(
        routeId=route_id,
        name=name,
        description=description,
        pois=items,
        estimatedDuration=_estimate_duration(ordered),
        highlights=[p["name"] for p in ordered[:3]],
        matchScore=round(match_score, 2),
    )


def _pick_pois_for_route(
    scored: list[tuple[float, dict]],
    count: int,
    exclude_ids: set[str],
) -> list[dict]:
    selected: list[dict] = []
    for score, poi in scored:
        if poi["id"] in exclude_ids:
            continue
        if score <= 0 and exclude_ids:
            continue
        selected.append(poi)
        if len(selected) >= count:
            break
    if len(selected) < 3:
        for _, poi in scored:
            if poi["id"] not in exclude_ids and poi not in selected:
                selected.append(poi)
            if len(selected) >= 3:
                break
    return selected[:count]


def _get_preset_routes(data: dict) -> list[dict]:
    presets = data.get("presetRoutes") or []
    if presets:
        return presets
    # 从 POI 按 LS/NH 分组生成默认路线
    pois = data.get("pois", [])
    lingshan_ids = [p["id"] for p in pois if str(p.get("spotId", "")).startswith("LS-")]
    nianhua_ids = [p["id"] for p in pois if str(p.get("spotId", "")).startswith("NH-")]
    routes = []
    for template in DEFAULT_ROUTES:
        if "lingshan" in template["routeId"] and lingshan_ids:
            routes.append({**template, "poiIds": lingshan_ids[:4]})
        elif "nianhua" in template["routeId"] and nianhua_ids:
            routes.append({**template, "poiIds": nianhua_ids[:4]})
    return routes or DEFAULT_ROUTES


def get_scenic_area_info() -> dict:
    data = _load_poi_data()
    return {
        "scenicAreaId": data.get("scenicAreaId", "lingshan_scenic"),
        "scenicAreaName": data.get("scenicAreaName", "灵山胜境"),
        "center": data.get("center"),
        "dataSource": data.get("dataSource"),
    }


def _route_name_for_preferences(preferences: list[str], index: int) -> str:
    if not preferences:
        return DEFAULT_ROUTES[index]["name"]
    primary = preferences[index % len(preferences)]
    return ROUTE_NAME_TEMPLATES.get(primary, f"个性化推荐线 {index + 1}")


def _route_description(preferences: list[str], pois: list[dict]) -> str:
    if preferences:
        pref_text = "、".join(preferences)
        return f"根据您的兴趣「{pref_text}」为您精选 {len(pois)} 个景点"
    return f"经典游览路线，涵盖 {len(pois)} 个代表性景点"


def recommend_routes(preferences: list[str] | None = None) -> list[RouteItem]:
    """
    根据兴趣偏好返回 2 条推荐路线。

    :param preferences: 兴趣标签，如 ["history", "nature"]
    :return: 2 条 RouteItem，每条含 3~4 个 POI
    """
    data = _load_poi_data()
    all_pois: list[dict] = data["pois"]
    prefs = _normalize_preferences(preferences or [])

    if not prefs:
        routes: list[RouteItem] = []
        poi_map = {p["id"]: p for p in all_pois}
        for i, template in enumerate(_get_preset_routes(data)[:2]):
            poi_ids = template.get("poiIds") or []
            poi_dicts = [poi_map[pid] for pid in poi_ids if pid in poi_map]
            if len(poi_dicts) < 3:
                continue
            routes.append(
                _build_route(
                    template.get("routeId", f"route_preset_{i}"),
                    template.get("name", f"推荐路线 {i + 1}"),
                    template.get("description", _route_description([], poi_dicts)),
                    poi_dicts[:4],
                    match_score=1.0,
                )
            )
        if routes:
            return routes

    scored = sorted(
        [(_score_poi(p, prefs), p) for p in all_pois],
        key=lambda x: x[0],
        reverse=True,
    )

    route1_pois = _pick_pois_for_route(scored, count=4, exclude_ids=set())
    route1_ids = {p["id"] for p in route1_pois}
    route1_score = sum(_score_poi(p, prefs) for p in route1_pois) / max(len(route1_pois), 1)

    route2_pois = _pick_pois_for_route(scored, count=4, exclude_ids=route1_ids)
    route2_score = sum(_score_poi(p, prefs) for p in route2_pois) / max(len(route2_pois), 1)

    return [
        _build_route(
            "route_custom_01",
            _route_name_for_preferences(prefs, 0),
            _route_description(prefs, route1_pois),
            route1_pois,
            route1_score,
        ),
        _build_route(
            "route_custom_02",
            _route_name_for_preferences(prefs, 1),
            _route_description(prefs, route2_pois),
            route2_pois,
            route2_score,
        ),
    ]


def get_all_pois() -> list[PoiItem]:
    """返回全部 POI（供调试或地图展示）。"""
    data = _load_poi_data()
    return [_poi_to_item(p) for p in data["pois"]]
