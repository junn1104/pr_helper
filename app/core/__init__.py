from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    app_name: str = "Presentation Coach AI"
    app_version: str = "0.1.0"

    sensevoice_device: str = "cpu"

    max_audio_size_mb: int = 100

    database_url: str = "sqlite:///./app.db"

    # GEMINI_API_KEY, GEMINI_MODEL 등 이 모델에 선언되지 않은
    # .env 값들은 각 서비스가 os.getenv()로 직접 읽는다.
    # extra="ignore"가 없으면 .env에 있는 미선언 키 때문에
    # Settings() 생성 자체가 ValidationError로 실패한다.
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()