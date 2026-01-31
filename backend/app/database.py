from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=(settings.ENV == "dev"),
)


def get_session():
    with Session(engine) as session:
        yield session


def init_db():
    SQLModel.metadata.create_all(engine)
