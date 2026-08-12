import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["GMAIL_ADDRESS"] = "test@example.com"
os.environ["GMAIL_APP_PASSWORD"] = "test-app-password"

import pytest
from fastapi.testclient import TestClient

import main
from database import Base, SessionLocal, engine
from limiter import limiter


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture(autouse=True)
def _clean_state():
    yield
    limiter.reset()
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()
