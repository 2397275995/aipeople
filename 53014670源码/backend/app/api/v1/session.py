from fastapi import APIRouter

from app.schemas.chat import ApiResponse, SessionLogRequest
from app.utils.response import success

router = APIRouter(prefix="/session", tags=["Session"])


@router.post("/log", response_model=ApiResponse[None])
async def session_log(request: SessionLogRequest) -> ApiResponse[None]:
    """会话日志异步上报占位。"""
    # TODO: 写入数据库 / 消息队列，供 M7/M8 分析
    _ = request
    return success(None, message="logged")
