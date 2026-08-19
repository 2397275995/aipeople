"""
ASR 语音识别 API。

POST /api/v1/asr/recognize — 接收 multipart/form-data 音频，返回识别文本。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.schemas.chat import ApiResponse, AsrRecognizeData
from app.services.asr_service import (
    ASREmptyResultError,
    ASRError,
    ASRInvalidAudioError,
    ASRService,
    ASRTooShortError,
)
from app.utils.response import success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/asr", tags=["ASR"])

_asr_service = ASRService()


def get_asr_service() -> ASRService:
    return _asr_service


@router.post("/recognize", response_model=ApiResponse[AsrRecognizeData])
async def asr_recognize(
    audio: UploadFile = File(..., description="WAV 音频文件，16kHz mono"),
    sessionId: str = Form(..., description="会话 ID"),
    lang: str = Form(default="zh", description="语言代码，默认 zh"),
    asr_service: ASRService = Depends(get_asr_service),
) -> ApiResponse[AsrRecognizeData]:
    """
    语音识别接口。

    接收前端 Press-to-talk 录制的 WAV 音频，调用 Whisper 转写为文本。

    响应 data 字段：
    ```json
    { "text": "识别文本", "confidence": 0.9, "durationMs": 3200 }
    ```
    """
    _ = sessionId  # 预留：后续可用于会话级 ASR 日志

    if not audio.filename and not audio.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未上传音频文件",
        )

    audio_bytes = await audio.read()
    logger.info(
        "asr/recognize session=%s filename=%s size=%d content_type=%s",
        sessionId,
        audio.filename,
        len(audio_bytes),
        audio.content_type,
    )

    try:
        result = await asr_service.recognize(audio_bytes, lang=lang)
        return success(AsrRecognizeData(**result))
    except ASRTooShortError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ASRInvalidAudioError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ASREmptyResultError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ASRError as exc:
        logger.exception("ASR 识别失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"语音识别失败: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("ASR 未知错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"语音识别服务异常: {exc}",
        ) from exc
