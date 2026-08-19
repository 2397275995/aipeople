from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import httpx

from app.core.config import settings
from app.schemas.chat import ApiResponse
from app.utils.response import success
from app.services.xfyun_avatar_service import video_gen_client

router = APIRouter(prefix="/avatar", tags=["Avatar"])


@router.get("/config", response_model=ApiResponse[dict])
async def get_avatar_config() -> ApiResponse[dict]:
    return success({
        "appId": settings.XFYUN_APP_ID,
        "apiKey": settings.XFYUN_API_KEY,
        "apiSecret": settings.XFYUN_API_SECRET,
        "sceneId": settings.XFYUN_SCENE_ID,
        "avatarId": settings.XFYUN_AVATAR_ID,
        "vcn": settings.XFYUN_VCN,
    })


@router.get("/stream-proxy/{full_path:path}")
async def stream_proxy(full_path: str):
    try:
        url = f"https://{full_path}"
        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                headers = {
                    k: v for k, v in response.headers.items()
                    if k.lower() not in ("content-length", "transfer-encoding", "host")
                }
                headers["Access-Control-Allow-Origin"] = "*"
                headers["Content-Type"] = "video/x-flv"
                return StreamingResponse(
                    response.aiter_bytes(),
                    status_code=response.status_code,
                    headers=headers,
                    media_type="video/x-flv",
                )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=exc.response.status_code if exc.response else 500, detail=str(exc)) from exc


@router.post("/start", response_model=ApiResponse[dict])
async def start_avatar() -> ApiResponse[dict]:
    return success({
        "mode": "video-generate",
        "appId": settings.XFYUN_APP_ID,
        "avatarId": settings.XFYUN_AVATAR_ID,
    })


@router.post("/talk", response_model=ApiResponse[dict])
async def talk_avatar(payload: dict) -> ApiResponse[dict]:
    text = payload.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="text 必填")
    try:
        result = await video_gen_client.generate_and_wait(text, payload.get("word_count", 120))
        return success({"reply": result.get("text") or text, **result})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stop", response_model=ApiResponse[dict])
async def stop_avatar(payload: dict) -> ApiResponse[dict]:
    return success({"stopped": True})


@router.post("/video/generate", response_model=ApiResponse[dict])
async def generate_video(payload: dict):
    prompt = payload.get("prompt")
    word_count = payload.get("word_count", 120)
    
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt 必填")
    
    try:
        result = await video_gen_client.generate_video(prompt, word_count)
        return success(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/video/query", response_model=ApiResponse[dict])
async def query_video_task(payload: dict):
    task_id = payload.get("task_id")
    
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id 必填")
    
    try:
        result = await video_gen_client.query_task(task_id)
        return success(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/video/generate-sync", response_model=ApiResponse[dict])
async def generate_video_sync(payload: dict):
    prompt = payload.get("prompt")
    word_count = payload.get("word_count", 120)
    
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt 必填")
    
    try:
        result = await video_gen_client.generate_and_wait(prompt, word_count)
        return success(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
