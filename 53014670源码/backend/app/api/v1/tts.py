"""
TTS 语音合成 API。

POST /api/v1/tts/synthesize — 独立 TTS 接口，供调试或前端预加载使用。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.chat import ApiResponse
from app.schemas.tts import TtsSynthesizeData, TtsSynthesizeRequest
from app.services.tts_service import TTSService
from app.utils.response import success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tts", tags=["TTS"])

_tts_service = TTSService()


def get_tts_service() -> TTSService:
    return _tts_service


@router.post("/synthesize", response_model=ApiResponse[TtsSynthesizeData])
async def tts_synthesize(
    request: TtsSynthesizeRequest,
    tts_service: TTSService = Depends(get_tts_service),
) -> ApiResponse[TtsSynthesizeData]:
    """
    文本转语音，返回音频 URL（及可选 base64）与 phoneme 口型时间戳。

    phonemes 示例：
    ```json
    [{ "phone": "本", "startMs": 0, "endMs": 120 }, ...]
    ```
    """
    try:
        if request.returnBase64:
            result = await tts_service.synthesize_with_base64(
                text=request.text,
                message_id=request.messageId,
                voice=request.voice,
            )
            data = TtsSynthesizeData(**result)
        else:
            payload = await tts_service.synthesize(
                text=request.text,
                message_id=request.messageId,
                voice=request.voice,
            )
            data = TtsSynthesizeData(
                audioUrl=payload.audioUrl,
                durationMs=payload.durationMs,
                phonemes=payload.phonemes,
            )
        return success(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("TTS 合成失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS 合成失败: {exc}",
        ) from exc
