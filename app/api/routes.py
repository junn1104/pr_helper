import json
import os
import tempfile
import uuid
import wave
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
)

from sqlmodel import (
    Session,
    select,
)

from app.api.deps import get_current_device
from app.core.database import get_session

from app.models.analysis_record import AnalysisRecord
from app.models.device import Device

from app.schemas.analysis_response import (
    AnalysisResponse,
)

from app.services.audio_converter import (
    AudioConverter,
)

from app.schemas.device_response import (
    DeviceTokenResponse
)

from app.schemas.history_response import (
    HistoryListResponse
)

from app.services.presentation_analysis_service import (
    PresentationAnalysisService,
)


router = APIRouter()


presentation_service = None


MAX_FILE_SIZE = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".wav",
    ".m4a",
}


def get_presentation_service():
    global presentation_service

    if presentation_service is None:
        presentation_service = (
            PresentationAnalysisService()
        )

    return presentation_service


def validate_wav(
    file_path: str,
):
    try:
        with wave.open(
            file_path,
            "rb",
        ) as wav_file:

            channels = (
                wav_file.getnchannels()
            )

            sample_rate = (
                wav_file.getframerate()
            )

            frames = (
                wav_file.getnframes()
            )

            if frames <= 0:
                raise ValueError(
                    "빈 WAV 파일입니다."
                )

            if channels <= 0:
                raise ValueError(
                    "유효하지 않은 채널 수입니다."
                )

            if sample_rate <= 0:
                raise ValueError(
                    "유효하지 않은 샘플링 레이트입니다."
                )

    except wave.Error:
        raise HTTPException(
            status_code=400,
            detail=(
                "실제 WAV 오디오 파일이 아닙니다."
            ),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post(
    "/api/device/register",
    response_model=DeviceTokenResponse,
)
def register_device(
    session: Session = Depends(
        get_session
    ),
):
    # 로그인/회원가입 없이 기기(브라우저/앱)를 구분하기 위한
    # 익명 토큰 발급. 발급받은 토큰은 클라이언트가 로컬에
    # 저장해두고 이후 모든 요청에 X-Device-Token 헤더로 보낸다.

    device = Device(
        token=str(
            uuid.uuid4()
        )
    )

    session.add(
        device
    )

    session.commit()

    session.refresh(
        device
    )

    return {
        "token": device.token
    }


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
)
async def analyze_presentation(
    file: UploadFile = File(...),
    session: Session = Depends(
        get_session
    ),
    device: Device = Depends(
        get_current_device
    ),
):

    filename = (
        file.filename
        or ""
    )

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "현재는 WAV, M4A 파일만 지원합니다."
            ),
        )

    original_temp_path = None
    converted_wav_path = None

    try:
        # 업로드된 원본 확장자를 그대로 유지해서
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension,
        ) as temp_file:

            original_temp_path = (
                temp_file.name
            )

            total_size = 0

            audio_chunks = []

            while True:
                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total_size += len(
                    chunk
                )

                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "파일 크기는 최대 50MB까지 지원합니다."
                        ),
                    )

                audio_chunks.append(
                    chunk
                )

                temp_file.write(
                    chunk
                )

        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "빈 파일은 업로드할 수 없습니다."
                ),
            )

        # 분석에 실제로 사용할 WAV 경로
        analysis_path = (
            original_temp_path
        )

        # M4A인 경우 WAV로 변환
        if extension == ".m4a":

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".wav",
            ) as wav_temp_file:

                converted_wav_path = (
                    wav_temp_file.name
                )

            try:
                AudioConverter.convert_to_wav(
                    original_temp_path,
                    converted_wav_path,
                )

            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "M4A 파일을 WAV로 변환하는 중 "
                        f"오류가 발생했습니다: {str(e)}"
                    ),
                )

            analysis_path = (
                converted_wav_path
            )

        # WAV 자체 업로드 또는
        # M4A → WAV 변환 결과 검증
        validate_wav(
            analysis_path
        )

        service = (
            get_presentation_service()
        )

        result = service.analyze(
            analysis_path
        )

        speech = result.get(
            "speech",
            {},
        )

        risk = result.get(
            "risk",
            {},
        )

        response_payload = {
            "transcript": (
                result.get(
                    "transcript",
                    "",
                )
            ),

            "duration": (
                result.get(
                    "duration",
                    0,
                )
            ),

            "speech": {
                "word_count": (
                    speech.get(
                        "word_count",
                        0,
                    )
                ),

                "presentation_duration": (
                    speech.get(
                        "presentation_duration",
                        0,
                    )
                ),

                "speech_time": (
                    speech.get(
                        "speech_time",
                        0,
                    )
                ),

                "presentation_rate": (
                    speech.get(
                        "presentation_rate",
                        0,
                    )
                ),

                "articulation_rate": (
                    speech.get(
                        "articulation_rate",
                        0,
                    )
                ),

                "pace_level": (
                    speech.get(
                        "pace_level",
                        "unknown",
                    )
                ),

                "internal_pause_time": (
                    speech.get(
                        "internal_pause_time",
                        0,
                    )
                ),

                "internal_pause_ratio": (
                    speech.get(
                        "internal_pause_ratio",
                        0,
                    )
                ),

                "internal_pauses": (
                    speech.get(
                        "internal_pauses",
                        [],
                    )
                ),
            },

            "fillers": (
                result.get(
                    "fillers",
                    [],
                )
            ),

            "risk": {
                "overall_score": (
                    risk.get(
                        "overall_score",
                        0,
                    )
                ),

                "overall_level": (
                    risk.get(
                        "overall_level",
                        "low",
                    )
                ),

                "heatmap": (
                    risk.get(
                        "heatmap",
                        [],
                    )
                ),
            },

            "coaching": (
                result.get(
                    "coaching",
                    {},
                )
            ),
        }

        try:
            record = AnalysisRecord(
                device_id=device.id,
                filename=filename,
                duration=response_payload[
                    "duration"
                ],
                audio_data=b"".join(
                    audio_chunks
                ),
                result_json=json.dumps(
                    response_payload,
                    ensure_ascii=False,
                ),
                overall_score=risk.get(
                    "overall_score",
                    0,
                ),
                overall_level=risk.get(
                    "overall_level",
                    "low",
                ),
            )

            session.add(
                record
            )

            session.commit()

        except Exception:
            # 분석 자체는 성공했으므로, 히스토리 저장이
            # 실패하더라도 분석 결과는 그대로 응답한다.
            session.rollback()

        return response_payload

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"분석 중 오류가 발생했습니다: {str(e)}"
            ),
        )

    finally:
        try:
            await file.close()
        except Exception:
            pass

        if (
            original_temp_path
            and os.path.exists(
                original_temp_path
            )
        ):
            try:
                os.remove(
                    original_temp_path
                )
            except OSError:
                pass

        if (
            converted_wav_path
            and os.path.exists(
                converted_wav_path
            )
        ):
            try:
                os.remove(
                    converted_wav_path
                )
            except OSError:
                pass


def _get_owned_record(
    record_id: int,
    session: Session,
    device: Device,
) -> AnalysisRecord:

    record = session.exec(
        select(
            AnalysisRecord
        ).where(
            AnalysisRecord.id == record_id,
            AnalysisRecord.device_id == device.id,
        )
    ).first()

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "해당 분석 기록을 찾을 수 없습니다."
            ),
        )

    return record


@router.get(
    "/api/history",
    response_model=HistoryListResponse,
)
def list_history(
    session: Session = Depends(
        get_session
    ),
    device: Device = Depends(
        get_current_device
    ),
):
    # 마이페이지 목록 조회. 로그인 없이
    # X-Device-Token으로 본인 기록만 필터링한다.

    records = session.exec(
        select(
            AnalysisRecord
        ).where(
            AnalysisRecord.device_id == device.id
        ).order_by(
            AnalysisRecord.created_at.desc()
        )
    ).all()

    return {
        "items": [
            {
                "id": record.id,
                "filename": record.filename,
                "duration": record.duration,
                "overall_score": record.overall_score,
                "overall_level": record.overall_level,
                "created_at": record.created_at,
            }
            for record in records
        ]
    }


@router.get(
    "/api/history/{record_id}",
    response_model=AnalysisResponse,
)
def get_history_detail(
    record_id: int,
    session: Session = Depends(
        get_session
    ),
    device: Device = Depends(
        get_current_device
    ),
):
    # 저장 당시의 분석 결과(AnalysisResponse)를
    # 그대로 복원해 반환한다.

    record = _get_owned_record(
        record_id,
        session,
        device,
    )

    return json.loads(
        record.result_json
    )


@router.get(
    "/api/history/{record_id}/audio",
)
def get_history_audio(
    record_id: int,
    session: Session = Depends(
        get_session
    ),
    device: Device = Depends(
        get_current_device
    ),
):
    # 재생/다시듣기용 원본 오디오. Postgres에는
    # bytea로, SQLite에는 BLOB으로 저장되어 있다.
    #
    # audio_data는 업로드된 원본 그대로(WAV 또는 M4A)
    # 저장되므로, 저장된 파일 확장자에 맞는 media_type을
    # 사용해야 한다.

    record = _get_owned_record(
        record_id,
        session,
        device,
    )

    extension = os.path.splitext(
        record.filename
    )[1].lower()

    media_type = (
        "audio/mp4"
        if extension == ".m4a"
        else "audio/wav"
    )

    return Response(
        content=record.audio_data,
        media_type=media_type,
    )