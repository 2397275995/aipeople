#!/usr/bin/env python3
"""从「示范景区公开资料包」提取 POI 并生成 scenic_pois.json。"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import pandas as pd
from docx import Document

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.demo_materials import find_official_package_dir  # noqa: E402

# 无锡灵山胜境 / 拈花湾（官方资料包景区）
LINSHAN_CENTER = {"lat": 31.431, "lng": 120.098}

COORDINATES: dict[str, tuple[float, float]] = {
    "灵山大照壁": (31.4282, 120.0968),
    "五明桥": (31.4288, 120.0972),
    "佛足坛": (31.4294, 120.0976),
    "五智门": (31.4300, 120.0980),
    "菩提大道": (31.4306, 120.0984),
    "九龙灌浴": (31.4310, 120.0986),
    "降魔浮雕": (31.4312, 120.0987),
    "阿育王柱": (31.4314, 120.0988),
    "百子戏弥勒": (31.4315, 120.0989),
    "祥符禅寺": (31.4316, 120.0990),
    "灵山大佛": (31.4318, 120.0992),
    "佛教文化博览馆": (31.4320, 120.0995),
    "灵山梵宫": (31.4325, 120.1000),
    "五印坛城": (31.4330, 120.1005),
    "曼飞龙塔": (31.4335, 120.1010),
    "无尽意斋": (31.4340, 120.1012),
    "拈花广场": (31.4385, 120.0745),
    "梵天花海": (31.4390, 120.0750),
    "香月花街": (31.4395, 120.0755),
    "拈花堂": (31.4400, 120.0760),
    "五灯湖": (31.4405, 120.0765),
    "鹿鸣谷": (31.4410, 120.0770),
}

TAG_RULES: list[tuple[str, list[str]]] = [
    (r"大佛|梵宫|寺|佛|塔|坛|禅|印|弥勒|九龙", ["history", "culture"]),
    (r"花海|湖|谷|林|鹿|广场|街", ["nature", "photo", "family"]),
    (r"博览|博物馆|纪念馆|斋", ["history", "culture"]),
]


def slugify(spot_id: str, name: str) -> str:
    base = re.sub(r"[^\w\u4e00-\u9fff]+", "_", f"{spot_id}_{name}").strip("_")
    return f"poi_{base[:56]}"


def parse_structure_docx(docx_path: Path) -> list[dict]:
    doc = Document(docx_path)
    pois: list[dict] = []
    for table in doc.tables:
        rows = [[c.text.strip() for c in row.cells] for row in table.rows]
        if len(rows) < 2:
            continue
        for row in rows[1:]:
            if len(row) < 3 or not row[2].strip():
                continue
            pois.append(
                {
                    "area": row[0].strip(),
                    "spot_id": row[1].strip(),
                    "name": row[2].strip(),
                    "location": row[3].strip() if len(row) > 3 else "",
                    "structure": row[4].strip() if len(row) > 4 else "",
                    "function": row[5].strip() if len(row) > 5 else "",
                    "culture": row[6].strip() if len(row) > 6 else "",
                    "detail": row[7].strip() if len(row) > 7 else "",
                    "service": row[9].strip() if len(row) > 9 else "",
                }
            )
    return pois


def load_xlsx_stats(xlsx_path: Path, poi_names: list[str]) -> dict[str, dict]:
    df = pd.read_excel(xlsx_path)
    if "attraction_name" not in df.columns:
        return {}
    name_set = set(poi_names)
    sub = df[df["attraction_name"].isin(name_set)]
    stats: dict[str, dict] = {}
    for name, group in sub.groupby("attraction_name"):
        stats[name] = {
            "visits": int(len(group)),
            "avgStayMinutes": round(float(group["stay_duration"].mean()), 1)
            if "stay_duration" in group.columns and group["stay_duration"].notna().any()
            else None,
            "avgSatisfaction": round(float(group["satisfaction"].mean()), 2)
            if "satisfaction" in group.columns and group["satisfaction"].notna().any()
            else None,
        }
    return stats


def infer_tags(name: str, function: str, area: str) -> list[str]:
    text = f"{name} {function} {area}"
    tags: list[str] = []
    for pattern, tgs in TAG_RULES:
        if re.search(pattern, text):
            for t in tgs:
                if t not in tags:
                    tags.append(t)
    return tags or ["culture"]


def estimate_visit_minutes(structure: str, avg_stay: float | None) -> int:
    if avg_stay and avg_stay > 0:
        return max(15, min(120, int(avg_stay)))
    if re.search(r"梵宫|大佛|博览", structure):
        return 60
    if re.search(r"花海|广场|街", structure):
        return 45
    return 35


def geocode_poi(name: str, spot_id: str, index: int) -> tuple[float, float]:
    if name in COORDINATES:
        return COORDINATES[name]
    if spot_id.startswith("NH-"):
        base_lat, base_lng = 31.4385, 120.0745
        offset = int(spot_id.split("-")[-1]) if "-" in spot_id else index
        return base_lat + offset * 0.0004, base_lng + offset * 0.0003
    base_lat, base_lng = LINSHAN_CENTER["lat"], LINSHAN_CENTER["lng"]
    angle = index * 0.35
    return base_lat + math.sin(angle) * 0.0015, base_lng + math.cos(angle) * 0.0012


def build_description(poi: dict) -> str:
    parts = [poi.get("location"), poi.get("structure"), poi.get("function"), poi.get("culture"), poi.get("detail")]
    text = "。".join(p for p in parts if p)
    return (text[:600] if text else poi["name"]).strip()


def build_preset_routes(pois: list[dict]) -> list[dict]:
    lingshan = [p for p in pois if p.get("spotId", "").startswith("LS-")]
    nianhua = [p for p in pois if p.get("spotId", "").startswith("NH-")]

    def route(route_id: str, name: str, desc: str, items: list[dict]) -> dict:
        return {
            "routeId": route_id,
            "name": name,
            "description": desc,
            "poiIds": [p["id"] for p in items[:4]],
            "highlights": [p["name"] for p in items[:3]],
        }

    routes: list[dict] = []
    if len(lingshan) >= 3:
        routes.append(
            route(
                "route_lingshan_classic",
                "灵山胜境朝圣线",
                "沿中轴线游览灵山大照壁、九龙灌浴、灵山大佛、灵山梵宫等核心景点，感受佛教文化与建筑艺术。",
                lingshan,
            )
        )
    if len(nianhua) >= 3:
        routes.append(
            route(
                "route_nianhua_town",
                "拈花湾禅意休闲线",
                "漫步拈花广场、梵天花海、香月花街与五灯湖，体验禅意小镇的雅致与自然之美。",
                nianhua,
            )
        )
    return routes


def generate_scenic_pois(pkg_dir: Path | None = None) -> dict:
    pkg = pkg_dir or find_official_package_dir()
    docx_files = list(pkg.glob("*.docx"))
    structure_docx = next(
        (p for p in docx_files if "建筑结构" in p.name or "数据集" in p.name),
        docx_files[0] if docx_files else None,
    )
    if not structure_docx:
        raise FileNotFoundError("资料包中未找到 docx 景点结构化数据集")

    raw_pois = parse_structure_docx(structure_docx)
    if not raw_pois:
        raise ValueError(f"未能从 {structure_docx.name} 解析景点表格")

    xlsx_path = next(iter(pkg.glob("*.xlsx")), None)
    xlsx_stats = load_xlsx_stats(xlsx_path, [p["name"] for p in raw_pois]) if xlsx_path else {}

    pois_out: list[dict] = []
    used_ids: set[str] = set()
    for idx, raw in enumerate(raw_pois):
        name = raw["name"]
        spot_id = raw["spot_id"]
        poi_id = slugify(spot_id, name)
        if poi_id in used_ids:
            poi_id = f"{poi_id}_{idx}"
        used_ids.add(poi_id)

        stats = xlsx_stats.get(name, {})
        lat, lng = geocode_poi(name, spot_id, idx)
        tags = infer_tags(name, raw.get("function", ""), raw.get("area", ""))
        visit = estimate_visit_minutes(raw.get("structure", ""), stats.get("avgStayMinutes"))

        pois_out.append(
            {
                "id": poi_id,
                "name": name,
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "description": build_description(raw),
                "tags": tags,
                "visitMinutes": visit,
                "area": raw.get("area", ""),
                "spotId": spot_id,
                "location": raw.get("location", ""),
                "sourceDoc": structure_docx.name,
            }
        )

    return {
        "scenicAreaId": "lingshan_scenic",
        "scenicAreaName": "灵山胜境",
        "center": LINSHAN_CENTER,
        "dataSource": pkg.name,
        "pois": pois_out,
        "presetRoutes": build_preset_routes(pois_out),
    }


def main() -> None:
    data = generate_scenic_pois()
    out_path = BACKEND_ROOT / "data" / "scenic_pois.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"OK: {out_path} | pois={len(data['pois'])} routes={len(data['presetRoutes'])}"
    )


if __name__ == "__main__":
    main()
