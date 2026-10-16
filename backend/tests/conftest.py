"""Test fixtures.

The application normally talks to PostgreSQL. Tests must never touch a real
database, so every test gets a fresh in-memory SQLite database and the app's
`get_db` dependency is overridden to use it.
"""

import os

# Must be set before the app is imported: app.database builds its engine at import.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # one shared connection so the in-memory DB persists
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def ticket_payload():
    return {
        "title": "Cannot reset my password",
        "description": "The reset email never arrives.",
        "requester_email": "priya@example.com",
        "category": "account",
        "priority": "high",
    }


@pytest.fixture()
def create_ticket(client, ticket_payload):
    def _create(**overrides):
        response = client.post("/api/tickets", json={**ticket_payload, **overrides})
        assert response.status_code == 201, response.text
        return response.json()

    return _create
