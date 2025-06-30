import os
import pytest
from fastapi.testclient import TestClient
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.config import settings
from app.security import security_manager

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

@pytest.fixture(scope="module")
def test_user_token():

    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "phone": "1234567890",
        "password": "testpassword",
        "is_botanist": False
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200, f"Création d'utilisateur échouée: {response.json()}"

    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    response = client.post("/token", data=login_data)
    assert response.status_code == 200, f"Login échoué: {response.json()}"
    token_data = response.json()
    
    return {
        "user_id": response.json()["id"],
        "token": token_data["access_token"],
        "user_data": user_data
    }

@pytest.fixture(scope="module")
def test_botanist_token():

    botanist_data = {
        "email": "botanist@example.com",
        "username": "botanistuser",
        "phone": "0987654321",
        "password": "botanistpassword",
        "is_botanist": True
    }
    response = client.post("/users/", json=botanist_data)
    assert response.status_code == 200, f"Création de botaniste échouée: {response.json()}"

    login_data = {
        "username": botanist_data["email"],
        "password": botanist_data["password"]
    }
    response = client.post("/token", data=login_data)
    assert response.status_code == 200, f"Login échoué: {response.json()}"
    token_data = response.json()
    
    return {
        "user_id": response.json()["id"],
        "token": token_data["access_token"],
        "user_data": botanist_data
    }

def test_create_user():
    
    user_data = {
        "email": "newuser@example.com",
        "username": "newuser",
        "phone": "5555555555",
        "password": "newpassword",
        "is_botanist": False
    }
    response = client.post("/users/", json=user_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert data["phone"] == user_data["phone"]
    assert data["is_botanist"] == user_data["is_botanist"]
    assert "id" in data

def test_create_duplicate_user():
    
    user_data = {
        "email": "duplicate@example.com",
        "username": "duplicateuser",
        "phone": "1231231231",
        "password": "duplicatepassword",
        "is_botanist": False
    }

    response = client.post("/users/", json=user_data)
    assert response.status_code == 200

    response = client.post("/users/", json=user_data)
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

def test_get_current_user(test_user_token):
    
    headers = {"Authorization": f"Bearer {test_user_token['token']}"}
    response = client.get("/users/me/", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user_token["user_data"]["email"]
    assert data["username"] == test_user_token["user_data"]["username"]
    assert data["is_botanist"] == test_user_token["user_data"]["is_botanist"]

def test_update_user(test_user_token):
    
    user_id = test_user_token["user_id"]
    headers = {"Authorization": f"Bearer {test_user_token['token']}"}

    update_data = {
        "username": "updateduser",
        "phone": "9876543210"
    }
    
    response = client.put(f"/users/{user_id}", params=update_data, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == update_data["username"]
    assert data["phone"] == update_data["phone"]

    response = client.get("/users/me/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == update_data["username"]
    assert data["phone"] == update_data["phone"]

def test_unauthorized_user_update(test_user_token, test_botanist_token):
    
    botanist_id = test_botanist_token["user_id"]
    user_headers = {"Authorization": f"Bearer {test_user_token['token']}"}

    update_data = {
        "username": "hackeduser",
        "phone": "1111111111"
    }
    
    response = client.put(f"/users/{botanist_id}", params=update_data, headers=user_headers)

    assert response.status_code == 403
    assert "Not authorized to update other users" in response.json()["detail"]

def test_login_with_wrong_credentials():
    
    login_data = {
        "username": "wrongemail@example.com",
        "password": "wrongpassword"
    }
    response = client.post("/token", data=login_data)
    
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

def test_authentication_without_token():
    
    response = client.get("/users/me/")
    
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

def test_delete_user(test_user_token):

    temp_user_data = {
        "email": "temp@example.com",
        "username": "tempuser",
        "phone": "9999999999",
        "password": "temppassword",
        "is_botanist": False
    }
    response = client.post("/users/", json=temp_user_data)
    assert response.status_code == 200
    temp_user_id = response.json()["id"]

    login_response = client.post("/token", data={
        "username": temp_user_data["email"],
        "password": temp_user_data["password"]
    })
    assert login_response.status_code == 200
    temp_token = login_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {temp_token}"}
    response = client.delete(f"/users/", params={"id": temp_user_id}, headers=headers)
    
    assert response.status_code == 200

    login_response = client.post("/token", data={
        "username": temp_user_data["email"],
        "password": temp_user_data["password"]
    })
    assert login_response.status_code == 401

def teardown_module():
    Base.metadata.drop_all(bind=engine)
    os.remove("./test_a_rosa_je.db")
