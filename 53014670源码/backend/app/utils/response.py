from typing import TypeVar

from pydantic import BaseModel

from app.schemas.chat import ApiResponse

T = TypeVar("T")


def success(data: T, message: str = "success") -> ApiResponse[T]:
    return ApiResponse(code=0, message=message, data=data)


def error(code: int, message: str) -> ApiResponse[None]:
    return ApiResponse(code=code, message=message, data=None)
