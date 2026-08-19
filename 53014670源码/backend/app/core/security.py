"""JWT 工具（管理员认证）。"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"


def create_admin_token(subject: str = "admin") -> str:
    """签发管理员 JWT。"""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": subject,
        "role": "admin",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_admin_token(token: str) -> str | None:
    """
    校验 JWT，返回 subject；无效返回 None。

    同时支持硬编码 ADMIN_API_TOKEN（非 JWT 字符串也可直接通过）。
    """
    if token == settings.ADMIN_API_TOKEN:
        return "admin"

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            return None
        return payload.get("sub") or "admin"
    except JWTError:
        return None
