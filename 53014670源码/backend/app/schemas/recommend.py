from pydantic import BaseModel, Field


class PoiItem(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    description: str
    tags: list[str]
    visitMinutes: int = 30


class RouteItem(BaseModel):
    routeId: str
    name: str
    description: str
    pois: list[PoiItem]
    estimatedDuration: int
    highlights: list[str]
    matchScore: float = 0.0


class RecommendRoutesData(BaseModel):
    routes: list[RouteItem]
    preferences: list[str] = Field(default_factory=list)
    scenicAreaId: str = "lingshan_scenic"
    scenicAreaName: str = "灵山胜境"


class RecommendRoutesRequest(BaseModel):
    preference: list[str] = Field(
        default_factory=list,
        description='兴趣标签，如 ["history", "nature"]',
        examples=[["history", "nature"]],
    )
