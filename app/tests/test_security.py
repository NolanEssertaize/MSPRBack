import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.config import settings
from app.security import security_manager
from app import models
import json

os.environ["TESTING"] = "True"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-for-testing"
os.environ["ENCRYPTION_ENABLED"] = "True"

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

def get_db_session():
    
    db = TestingSessionLocal()
    try:
        return db
    finally:
        db.close()

@pytest.fixture(scope="module")
def test_user_data():
    
    return {
        "email": "security@example.com",
        "username": "securityuser",
        "phone": "1122334455",
        "password": "securepassword",
        "is_botanist": False
    }

def test_user_data_encryption(test_user_data):

    response = client.post("/users/", json=test_user_data)
    assert response.status_code == 200
    user_id = response.json()["id"]

    db = get_db_session()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()

    assert db_user.email_encrypted != test_user_data["email"]
    assert db_user.username_encrypted != test_user_data["username"]
    assert db_user.phone_encrypted != test_user_data["phone"]

    assert db_user.email_hash is not None
    assert db_user.username_hash is not None
    assert db_user.phone_hash is not None

    assert db_user.hashed_password != test_user_data["password"]

    decrypted_email = security_manager.decrypt_value(db_user.email_encrypted)
    decrypted_username = security_manager.decrypt_value(db_user.username_encrypted)
    decrypted_phone = security_manager.decrypt_value(db_user.phone_encrypted)
    
    assert decrypted_email == test_user_data["email"]
    assert decrypted_username == test_user_data["username"]
    assert decrypted_phone == test_user_data["phone"]

def test_token_expiration():

    original_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    settings.ACCESS_TOKEN_EXPIRE_MINUTES = 0  # Expire immédiatement

    user_data = {
        "email": "expiration@example.com",
        "username": "expirationuser",
        "phone": "9988776655",
        "password": "expirationpassword",
        "is_botanist": False
    }
    client.post("/users/", json=user_data)
    
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    response = client.post("/token", data=login_data)
    token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/users/me/", headers=headers)

    settings.ACCESS_TOKEN_EXPIRE_MINUTES = original_expire_minutes

    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]

def test_invalid_token():
    
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbnZhbGlkQGV4YW1wbGUuY29tIiwiZXhwIjoxOTU4NjU0NDAwfQ.invalid_signature"
    
    headers = {"Authorization": f"Bearer {invalid_token}"}
    response = client.get("/users/me/", headers=headers)
    
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]

def test_password_security(test_user_data):

    response = client.post("/users/", json=test_user_data)
    assert response.status_code == 200

    db = get_db_session()
    email_hash = security_manager.hash_value(test_user_data["email"])
    db_user = db.query(models.User).filter(models.User.email_hash == email_hash).first()

    assert test_user_data["password"] not in db_user.hashed_password

    login_data = {
        "username": test_user_data["email"],
        "password": test_user_data["password"]
    }
    response = client.post("/token", data=login_data)
    assert response.status_code == 200

    wrong_login_data = {
        "username": test_user_data["email"],
        "password": "wrongpassword"
    }
    response = client.post("/token", data=wrong_login_data)
    assert response.status_code == 401

def test_authorization_endpoints():

    protected_endpoints = [
        {"method": "GET", "url": "/users/me/"},
        {"method": "GET", "url": "/my_plants/"},
        {"method": "GET", "url": "/all_plants/"},
        {"method": "POST", "url": "/plants/", "params": {"name": "test", "location": "test"}, "files": {"photo": ("empty.jpg", b"")}},
        {"method": "GET", "url": "/care-requests/"}
    ]
    
    for endpoint in protected_endpoints:
        method = endpoint["method"]
        url = endpoint["url"]
        
        if method == "GET":
            response = client.get(url)
        elif method == "POST":
            params = endpoint.get("params", {})
            files = endpoint.get("files", {})
            response = client.post(url, data=params, files=files)

        assert response.status_code == 401, f"Endpoint {method} {url} ne nécessite pas d'authentification"

def test_cross_user_access_control(test_user_data):

    user1_data = {
        "email": "user1@example.com",
        "username": "user1",
        "phone": "1111111111",
        "password": "password1",
        "is_botanist": False
    }
    user2_data = {
        "email": "user2@example.com",
        "username": "user2",
        "phone": "2222222222",
        "password": "password2",
        "is_botanist": False
    }
    
    client.post("/users/", json=user1_data)
    client.post("/users/", json=user2_data)

    user1_login = {"username": user1_data["email"], "password": user1_data["password"]}
    user2_login = {"username": user2_data["email"], "password": user2_data["password"]}
    
    user1_token = client.post("/token", data=user1_login).json()["access_token"]
    user2_token = client.post("/token", data=user2_login).json()["access_token"]

    user1_headers = {"Authorization": f"Bearer {user1_token}"}
    user1_id = client.get("/users/me/", headers=user1_headers).json()["id"]

    user2_headers = {"Authorization": f"Bearer {user2_token}"}
    user2_id = client.get("/users/me/", headers=user2_headers).json()["id"]

    update_data = {"username": "hacked"}
    response = client.put(f"/users/{user2_id}", params=update_data, headers=user1_headers)

    assert response.status_code == 403
    assert "Not authorized to update other users" in response.json()["detail"]

def teardown_module():
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_a_rosa_je.db"):
        os.remove("./test_a_rosa_je.db")
