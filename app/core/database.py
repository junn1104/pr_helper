from sqlmodel import (
    SQLModel,
    Session,
    create_engine,
)

from app.core import settings


def _normalize_database_url(
    url: str,
) -> str:

    # Render 등 일부 플랫폼은 DATABASE_URL을
    # "postgres://"로 내려주는데, SQLAlchemy 1.4+에서는
    # "postgresql://"만 인식하므로 여기서 보정한다.

    if url.startswith(
        "postgres://"
    ):
        return (
            "postgresql://"
            + url[len("postgres://"):]
        )

    return url


DATABASE_URL = _normalize_database_url(
    settings.database_url
)


connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)


def init_db():
    # 데모/MVP 규모라 별도 마이그레이션 도구(Alembic) 없이
    # 앱 시작 시 테이블이 없으면 생성하는 방식으로 처리한다.

    from app.models import (  # noqa: F401
        device,
        analysis_record,
    )

    SQLModel.metadata.create_all(
        engine
    )


def get_session():
    with Session(engine) as session:
        yield session
