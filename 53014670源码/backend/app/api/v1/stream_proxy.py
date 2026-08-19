from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import httpx

router = APIRouter(prefix="/stream", tags=["Stream Proxy"])


@router.get("/proxy")
async def proxy_stream(url: str):
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                headers = {
                    k: v for k, v in response.headers.items()
                    if k.lower() not in ("content-length", "transfer-encoding")
                }
                headers["Access-Control-Allow-Origin"] = "*"
                return StreamingResponse(
                    response.aiter_bytes(),
                    status_code=response.status_code,
                    headers=headers,
                    media_type=response.headers.get("content-type", "video/flv"),
                )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
