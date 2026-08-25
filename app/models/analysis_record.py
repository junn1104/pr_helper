from datetime import datetime
from typing import Optional

from sqlmodel import (
    SQLModel,
    Field,
)


class AnalysisRecord(
    SQLModel,
    table=True,
):
    # 분석 결과 1건 = 마이페이지 히스토리의 아이템 1개.
    #
    # 이번 규모(모노/16kHz, 10분 캡 기준 세션당 최대 약 19MB)에서는
    # 별도 오브젝트 스토리지 없이 오디오 원본을 audio_data(bytea)에
    # 함께 저장한다. 보관 기간 정책(예: 30일 후 자동 삭제)은
    # 추후 로드맵으로 남겨둔다.

    id: Optional[int] = Field(
        default=None,
        primary_key=True,
    )

    device_id: int = Field(
        foreign_key="device.id",
        index=True,
    )

    filename: str

    duration: float

    audio_data: bytes

    result_json: str

    overall_score: int
    overall_level: str

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,
    )
