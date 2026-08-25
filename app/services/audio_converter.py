import subprocess
from pathlib import Path

import imageio_ffmpeg


class AudioConverter:
    """
    업로드된 오디오 파일을 분석용 WAV로 변환한다.

    출력 형식:
    - WAV
    - 16kHz
    - Mono
    - PCM 16-bit
    """

    @staticmethod
    def convert_to_wav(input_path: str, output_path: str) -> str:
        input_file = Path(input_path)
        output_file = Path(output_path)

        if not input_file.exists():
            raise FileNotFoundError(f"입력 오디오 파일을 찾을 수 없습니다: {input_path}")

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        command = [
            ffmpeg_exe,
            "-y",
            "-i",
            str(input_file),

            # 영상 스트림이 포함되어 있더라도 제거
            "-vn",

            # Mono
            "-ac",
            "1",

            # 16kHz
            "-ar",
            "16000",

            # 16-bit PCM WAV
            "-acodec",
            "pcm_s16le",

            str(output_file),
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "오디오 WAV 변환에 실패했습니다.\n"
                f"{result.stderr}"
            )

        if not output_file.exists():
            raise RuntimeError("WAV 변환 결과 파일이 생성되지 않았습니다.")

        return str(output_file)