from pathlib import Path

from fastapi import APIRouter

from app.api.v1 import asr, avatar, chat, recommend, session, stream_proxy, tts, xfyun_proxy
from app.api.v1.admin import analytics_api, dashboard_api, kb as admin_kb

api_v1_router = APIRouter()

api_v1_router.include_router(chat.router)
api_v1_router.include_router(asr.router)
api_v1_router.include_router(tts.router)
api_v1_router.include_router(avatar.router)
api_v1_router.include_router(recommend.router)
api_v1_router.include_router(session.router)
api_v1_router.include_router(stream_proxy.router)
api_v1_router.include_router(xfyun_proxy.router)
api_v1_router.include_router(dashboard_api.router)
api_v1_router.include_router(analytics_api.router)
api_v1_router.include_router(admin_kb.router)
