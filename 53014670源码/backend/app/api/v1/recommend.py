from fastapi import APIRouter, Query

from app.schemas.chat import ApiResponse
from app.schemas.recommend import RecommendRoutesData, RecommendRoutesRequest
from app.services.recommend_service import get_scenic_area_info, recommend_routes
from app.utils.response import success

router = APIRouter(prefix="/recommend", tags=["Recommend"])


@router.post("/routes", response_model=ApiResponse[RecommendRoutesData])
async def recommend_routes_post(
    body: RecommendRoutesRequest,
) -> ApiResponse[RecommendRoutesData]:
    """根据兴趣偏好推荐 2 条游览路线（每条 3~4 个 POI）。"""
    routes = recommend_routes(body.preference)
    area = get_scenic_area_info()
    return success(
        RecommendRoutesData(
            routes=routes,
            preferences=body.preference,
            scenicAreaId=area.get("scenicAreaId", "lingshan_scenic"),
            scenicAreaName=area.get("scenicAreaName", "灵山胜境"),
        ),
        message="路线推荐成功",
    )


@router.get("/routes", response_model=ApiResponse[RecommendRoutesData])
async def recommend_routes_get(
    preference: list[str] = Query(
        default=[],
        description='兴趣标签，可重复传参：?preference=history&preference=nature',
    ),
) -> ApiResponse[RecommendRoutesData]:
    """GET 方式获取推荐路线（便于浏览器调试）。"""
    routes = recommend_routes(preference)
    area = get_scenic_area_info()
    return success(
        RecommendRoutesData(
            routes=routes,
            preferences=preference,
            scenicAreaId=area.get("scenicAreaId", "lingshan_scenic"),
            scenicAreaName=area.get("scenicAreaName", "灵山胜境"),
        ),
        message="路线推荐成功",
    )
