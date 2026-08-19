from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from starlette.requests import Request

router = APIRouter(prefix="/xfyun", tags=["Xfyun Proxy"])

XFYUN_BASE_URL = "https://vms.cn-huadong-1.xf-yun.com"


@router.get("/{path:path}")
async def xfyun_get_proxy(path: str, request: Request):
    try:
        query_params = request.query_params
        url = f"{XFYUN_BASE_URL}/{path}"
        if query_params:
            url += f"?{query_params}"

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                headers = {
                    k: v for k, v in response.headers.items()
                    if k.lower() not in ("content-length", "transfer-encoding", "host")
                }
                headers["Access-Control-Allow-Origin"] = "*"
                return StreamingResponse(
                    response.aiter_bytes(),
                    status_code=response.status_code,
                    headers=headers,
                    media_type=response.headers.get("content-type", "application/octet-stream"),
                )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=exc.response.status_code if exc.response else 500, detail=str(exc)) from exc


@router.post("/{path:path}")
async def xfyun_post_proxy(path: str, request: Request):
    try:
        query_params = request.query_params
        body = await request.json()
        url = f"{XFYUN_BASE_URL}/{path}"
        if query_params:
            url += f"?{query_params}"

        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ("host", "content-length", "transfer-encoding", "connection")
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            resp_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in ("content-length", "transfer-encoding", "host")
            }
            resp_headers["Access-Control-Allow-Origin"] = "*"
            return {"status": response.status_code, "data": response.json()}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=exc.response.status_code if exc.response else 500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sdk/download")
async def download_sdk():
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("GET", "https://xfyun-doc.cn-bj.ufileos.com/static/16710928950557670/vms-web-sdk-2.0.0.zip") as response:
                response.raise_for_status()
                headers = {
                    k: v for k, v in response.headers.items()
                    if k.lower() not in ("content-length", "transfer-encoding", "host")
                }
                headers["Access-Control-Allow-Origin"] = "*"
                headers["Content-Disposition"] = "attachment; filename=vms-web-sdk-2.0.0.zip"
                return StreamingResponse(
                    response.aiter_bytes(),
                    status_code=response.status_code,
                    headers=headers,
                    media_type="application/zip",
                )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=exc.response.status_code if exc.response else 500, detail=str(exc)) from exc


@router.get("/sdk/{filename}")
async def get_sdk_file(filename: str):
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"https://vms.cn-huadong-1.xf-yun.com/api/sdk/{filename}"
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                headers = {
                    k: v for k, v in response.headers.items()
                    if k.lower() not in ("content-length", "transfer-encoding", "host")
                }
                headers["Access-Control-Allow-Origin"] = "*"
                return StreamingResponse(
                    response.aiter_bytes(),
                    status_code=response.status_code,
                    headers=headers,
                    media_type=response.headers.get("content-type", "application/javascript"),
                )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=exc.response.status_code if exc.response else 500, detail=str(exc)) from exc
