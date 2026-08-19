from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import Base, engine
from app.utils.db_migrate import apply_sqlite_patches


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动：建表、创建必要目录、预加载语音识别模型。"""
    import asyncio
    import logging

    from app.services.asr_service import FasterWhisperASR

    logger = logging.getLogger(__name__)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await apply_sqlite_patches(conn)
    Path(settings.KB_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.TTS_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path("./data").mkdir(parents=True, exist_ok=True)

    if settings.ASR_PROVIDER.lower() == "faster-whisper":
        try:
            logger.info("预加载 faster-whisper 模型（首次可能需数十秒）…")
            await asyncio.to_thread(FasterWhisperASR._load_model)
            logger.info("faster-whisper 模型已就绪")
        except Exception as exc:
            logger.warning("ASR 模型预加载失败，语音功能可能不可用: %s", exc)

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="景区导览服务 AI 数字人后端 API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # TTS 音频静态文件（Edge-TTS 合成结果）
    tts_dir = Path(settings.TTS_OUTPUT_DIR)
    tts_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static/tts", StaticFiles(directory=str(tts_dir)), name="tts_audio")

    return app
