from datetime import datetime
from typing import Optional

from sqlmodel import (
    SQLModel,
    Field,
)


class Device(
    SQLModel,
    table=True,
):
    # 로그인 없이 기기(브라우저)를 식별하기 위한
    # 익명 토큰. Flutter 앱은 최초 실행 시
    # /api/device/register 로 토큰을 발급받아
    # 로컬에 저장해두고, 이후 모든 요청에
    # X-Device-Token 헤더로 실어 보낸다.

    id: Optional[int] = Field(
        default=None,
        primary_key=True,
    )

    token: str = Field(
        index=True,
        unique=True,
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
