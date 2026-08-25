from fastapi import (
    Header,
    HTTPException,
    Depends,
)

from sqlmodel import (
    Session,
    select,
)

from app.core.database import get_session
from app.models.device import Device


def get_current_device(
    x_device_token: str = Header(
        None,
        alias="X-Device-Token",
    ),
    session: Session = Depends(
        get_session
    ),
) -> Device:

    if not x_device_token:
        raise HTTPException(
            status_code=401,
            detail=(
                "X-Device-Token 헤더가 없습니다. "
                "먼저 POST /api/device/register 로 "
                "기기 토큰을 발급받아야 합니다."
            ),
        )

    device = session.exec(
        select(
            Device
        ).where(
            Device.token == x_device_token
        )
    ).first()

    if device is None:
        raise HTTPException(
            status_code=401,
            detail=(
                "유효하지 않은 기기 토큰입니다. "
                "POST /api/device/register 로 "
                "새 토큰을 발급받아 주세요."
            ),
        )

    return device
