import os

# Setup test environment
os.environ["TESTING"] = "True"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-for-testing"
os.environ["ENCRYPTION_ENABLED"] = "True"
os.environ["TEST_DATABASE_URL"] = "sqlite:///./test_a_rosa_je.db"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_a_rosa_je.db"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# ensure photos dir exists
os.makedirs("photos", exist_ok=True)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_preflight_options():
    response = client.options("/some/random/path")
    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5000"
    assert "Access-Control-Allow-Methods" in response.headers


def test_static_photo_serving():
    filename = "test_main_photo.txt"
    path = os.path.join("photos", filename)
    with open(path, "w") as f:
        f.write("hello")

    response = client.get(f"/photos/{filename}")
    assert response.status_code == 200
    assert response.text == "hello"

    os.remove(path)
