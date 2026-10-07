import os
import pytest

# Ensure offline mock mode for fast and offline tests
os.environ["FAST_NLP"] = "1"
os.environ["USE_MOCK_MODEL"] = "1"
os.environ["SECRET_KEY"] = "test-secret-key-indic-sentiment-1234567890"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, Product, Review
from app.auth import hash_password, create_access_token

# In-memory SQLite engine for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_user(db_session):
    user = User(
        email="testuser@example.com",
        hashed_password=hash_password("testpassword123"),
        org_name="Test Enterprise"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Add sample product
    prod = Product(
        user_id=user.id,
        name="Test Smartphone X",
        category="Electronics"
    )
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    return user

@pytest.fixture(scope="function")
def auth_headers(test_user):
    token = create_access_token(data={"sub": str(test_user.id), "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}
