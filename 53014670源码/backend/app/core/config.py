from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "景区导览AI数字人"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    # 硬编码管理员 Token（开发简化；生产请更换）
    ADMIN_API_TOKEN: str = "scenic-admin-token-2026"

    # Knowledge Base
    KB_UPLOAD_DIR: str = "./data/uploads"

    # Database（默认 SQLite，会话日志 / 知识库元数据）
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/scenic_guide.db"

    # PostgreSQL（可选，docker-compose 环境覆盖 DATABASE_URL）
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "scenic_user"
    POSTGRES_PASSWORD: str = "scenic_pass"
    POSTGRES_DB: str = "scenic_guide"
    # 兼容旧配置；未设置 DATABASE_URL 时使用 SQLite
    # DATABASE_URL=postgresql+asyncpg://scenic_user:scenic_pass@localhost:5432/scenic_guide

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o"
    LLM_TIMEOUT: int = 30
    LLM_PROVIDER: str = "mock"  # mock | openai

    # ASR (语音识别)
    ASR_PROVIDER: str = "faster-whisper"  # faster-whisper | openai
    ASR_API_KEY: str = ""
    ASR_API_BASE: str = ""
    ASR_MODEL: str = "small"  # faster-whisper 模型: tiny/base/small/medium
    ASR_MODEL_PATH: str = ""  # 可选：本地模型目录，跳过在线下载
    ASR_HF_ENDPOINT: str = "https://hf-mirror.com"  # HuggingFace 镜像（国内网络）
    ASR_OPENAI_MODEL: str = "whisper-1"
    ASR_DEVICE: str = "cpu"
    ASR_COMPUTE_TYPE: str = "int8"
    ASR_TIMEOUT: int = 60
    ASR_MIN_DURATION_MS: int = 500
    ASR_MAX_FILE_SIZE: int = 10 * 1024 * 1024

    # TTS (语音合成 - Edge-TTS)
    TTS_VOICE: str = "zh-CN-XiaoxiaoNeural"
    TTS_RATE: str = "+0%"
    TTS_VOLUME: str = "+0%"
    TTS_OUTPUT_DIR: str = "./data/tts_cache"
    TTS_PUBLIC_BASE_URL: str = "http://localhost:8000"

    # RAG / Embedding / Chroma
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "scenic_docs"
    SCENIC_DOCS_DIR: str = "./data/scenic_docs"
    SCENIC_POIS_FILE: str = "./data/scenic_pois.json"
    SCENIC_AREA_ID: str = "lingshan_scenic"
    SCENIC_AREA_NAME: str = "灵山胜境"
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 3
    VECTOR_DB_URL: str = ""

    # Session Memory
    SESSION_MEMORY_MAX_TURNS: int = 3
    SESSION_MEMORY_TTL: int = 3600
    USE_REDIS_SESSION: bool = True

    # Object Storage
    OSS_ENDPOINT: str = ""
    OSS_ACCESS_KEY: str = ""
    OSS_SECRET_KEY: str = ""
    OSS_BUCKET: str = "scenic-guide"

    # XFYun Virtual Human
    XFYUN_API_KEY: str = ""
    XFYUN_API_SECRET: str = ""
    XFYUN_APP_ID: str = ""
    XFYUN_SCENE_ID: str = ""
    XFYUN_AVATAR_ID: str = ""
    XFYUN_VCN: str = "zh-CN-XiaoxiaoNeural"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
