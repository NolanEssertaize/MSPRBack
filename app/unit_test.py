import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import io
from app.main import app
from app.models import User, Plant
from app.database import get_db
from app.auth import get_current_user, create_access_token
from datetime import timedelta
from app.config import settings

# Create test client
client = TestClient(app)

# Mock database session
@pytest.fixture
def db_session():
    """Returns a mock database session for testing."""
    mock_db = MagicMock()
    return mock_db

# Mock authenticated user (regular user)
@pytest.fixture
def regular_user():
    """Returns a mock regular user for testing."""
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        phone="123456789",
        hashed_password="hashed_password",
        is_active=True,
        is_botanist=False
    )

# Mock authenticated user (botanist)
@pytest.fixture
def botanist_user():
    """Returns a mock botanist user for testing."""
    return User(
        id=2,
        username="testbotanist",
        email="botanist@example.com",
        phone="987654321",
        hashed_password="hashed_password",
        is_active=True,
        is_botanist=True
    )

# Mock plant
@pytest.fixture
def mock_plant():
    """Returns a mock plant for testing."""
    return Plant(
        id=1,
        name="Test Plant",
        location="Living Room",
        care_instructions="Water once a week",
        photo_url="photos/1_test.jpg",
        owner_id=1,
        in_care=False,
        plant_sitting=None
    )

# Override dependency to use mock database
@pytest.fixture(autouse=True)
def override_get_db(db_session):
    """Override the get_db dependency with our mock."""
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.pop(get_db, None)

# Override dependency to use mock authenticated user
@pytest.fixture
def override_auth_regular_user(regular_user):
    """Override the get_current_user dependency with our mock regular user."""
    app.dependency_overrides[get_current_user] = lambda: regular_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

# Override dependency to use mock authenticated botanist
@pytest.fixture
def override_auth_botanist(botanist_user):
    """Override the get_current_user dependency with our mock botanist user."""
    app.dependency_overrides[get_current_user] = lambda: botanist_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

# Helper function to create a test token
def create_test_token(user_email: str):
    """Create a test JWT token for a given user email."""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(
        data={"sub": user_email}, expires_delta=access_token_expires
    )

# ======= AUTHENTICATION TESTS =======

def test_login_success(db_session):
    """Test successful login with correct credentials."""
    # Arrange
    mock_user = User(
        email="test@example.com",
        hashed_password="$2b$12$tVg6YBLZQUXEPMt5FJXiCetxYTTOvHd80Vgoe2b4WRdMJJV0qiN1W"  # 'testpassword'
    )
    db_session.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Mock verify_password to return True
    with patch('app.auth.verify_password', return_value=True):
        # Act
        response = client.post(
            "/token",
            data={"username": "test@example.com", "password": "testpassword"}
        )
        
        # Assert
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"

def test_login_invalid_credentials(db_session):
    """Test login with invalid credentials returns 401."""
    # Arrange
    mock_user = User(
        email="test@example.com",
        hashed_password="$2b$12$tVg6YBLZQUXEPMt5FJXiCetxYTTOvHd80Vgoe2b4WRdMJJV0qiN1W"  # 'testpassword'
    )
    db_session.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Mock verify_password to return False
    with patch('app.auth.verify_password', return_value=False):
        # Act
        response = client.post(
            "/token",
            data={"username": "test@example.com", "password": "wrongpassword"}
        )
        
        # Assert
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

def test_login_nonexistent_user(db_session):
    """Test login with nonexistent user returns 401."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = None
    
    # Act
    response = client.post(
        "/token",
        data={"username": "nonexistent@example.com", "password": "testpassword"}
    )
    
    # Assert
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

# ======= USER MANAGEMENT TESTS =======

def test_create_user_success(db_session):
    """Test successful user creation."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = None
    
    # Mock get_password_hash
    with patch('app.auth.get_password_hash', return_value="hashed_password"):
        # Act
        response = client.post(
            "/users/",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "phone": "987654321",
                "password": "password123",
                "is_botanist": False
            }
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json()["email"] == "newuser@example.com"
        assert response.json()["username"] == "newuser"
        assert "hashed_password" not in response.json()
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()

def test_create_user_email_already_registered(db_session):
    """Test user creation with already registered email returns 400."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = User(
        email="existing@example.com"
    )
    
    # Act
    response = client.post(
        "/users/",
        json={
            "username": "existinguser",
            "email": "existing@example.com",
            "phone": "123456789",
            "password": "password123",
            "is_botanist": False
        }
    )
    
    # Assert
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]
    db_session.add.assert_not_called()
    db_session.commit.assert_not_called()

def test_get_current_user(override_auth_regular_user):
    """Test getting current user information."""
    # Act
    response = client.get("/users/me/")
    
    # Assert
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    assert response.json()["username"] == "testuser"

def test_edit_user_success(db_session, override_auth_regular_user, regular_user):
    """Test successful user update."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = regular_user
    
    # Act
    response = client.put(
        f"/users/{regular_user.id}?username=updateduser&phone=999999999"
    )
    
    # Assert
    assert response.status_code == 200
    assert regular_user.username == "updateduser"
    assert regular_user.phone == "999999999"
    db_session.commit.assert_called_once()

def test_edit_user_not_found(db_session, override_auth_regular_user):
    """Test updating non-existent user returns 404."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = None
    
    # Act
    response = client.put(
        "/users/999?username=updateduser"
    )
    
    # Assert
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]

def test_edit_other_user_unauthorized(db_session, override_auth_regular_user):
    """Test updating another user's profile returns 403."""
    # Act
    response = client.put(
        "/users/2?username=hacker"
    )
    
    # Assert
    assert response.status_code == 403
    assert "Not authorized to update other users" in response.json()["detail"]

def test_delete_user_success(db_session, override_auth_regular_user):
    """Test successful user deletion."""
    # Arrange
    mock_user = User(id=1, email="delete@example.com")
    db_session.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Act
    response = client.delete("/users/?id=1")
    
    # Assert
    assert response.status_code == 200
    db_session.delete.assert_called_once_with(mock_user)
    db_session.commit.assert_called_once()

def test_delete_user_not_found(db_session, override_auth_regular_user):
    """Test deleting non-existent user returns 404."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = None
    
    # Act
    response = client.delete("/users/?id=999")
    
    # Assert
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]

# ======= PLANT MANAGEMENT TESTS =======

def test_create_plant_success(db_session, override_auth_regular_user):
    """Test successful plant creation."""
    # Arrange
    db_session.add.return_value = None
    db_session.commit.return_value = None
    
    test_image = io.BytesIO(b"test image content")
    test_image.name = "test_plant.jpg"
    
    # Mock file operations
    with patch("builtins.open", MagicMock()):
        # Act
        response = client.post(
            "/plants/",
            data={
                "name": "Test Plant",
                "location": "Living Room",
                "care_instructions": "Water once a week"
            },
            files={"photo": ("test_plant.jpg", test_image, "image/jpeg")}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json()["name"] == "Test Plant"
        assert response.json()["location"] == "Living Room"
        assert response.json()["care_instructions"] == "Water once a week"
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()

def test_update_plant_success(db_session, override_auth_regular_user, mock_plant):
    """Test successful plant update."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = mock_plant
    
    # Mock file operations
    with patch("builtins.open", MagicMock()), patch("os.path.exists", return_value=False):
        # Act
        response = client.put(
            f"/plants/{mock_plant.id}?name=Updated%20Plant&location=Kitchen"
        )
        
        # Assert
        assert response.status_code == 200
        assert mock_plant.name == "Updated Plant"
        assert mock_plant.location == "Kitchen"
        db_session.commit.assert_called_once()

def test_update_plant_not_found(db_session, override_auth_regular_user):
    """Test updating non-existent plant returns 404."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = None
    
    # Act
    response = client.put(
        "/plants/999?name=Updated%20Plant"
    )
    
    # Assert
    assert response.status_code == 404
    assert "Plant not found" in response.json()["detail"]

def test_delete_plant_success(db_session, override_auth_regular_user, mock_plant):
    """Test successful plant deletion."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = mock_plant
    
    # Act
    response = client.delete("/plants?plant_id=1")
    
    # Assert
    assert response.status_code == 200
    db_session.delete.assert_called_once_with(mock_plant)
    db_session.commit.assert_called_once()

def test_delete_plant_not_found(db_session, override_auth_regular_user):
    """Test deleting non-existent plant returns 404."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = None
    db_session.delete.side_effect = Exception("Not found")
    
    # Act
    response = client.delete("/plants?plant_id=999")
    
    # Assert
    assert response.status_code == 404
    assert "The plant was not found" in response.json()["detail"]

def test_list_user_plants(db_session, override_auth_regular_user):
    """Test listing user's plants."""
    # Arrange
    mock_plants = [
        Plant(id=1, name="Plant 1", photo_url="photos/1.jpg"),
        Plant(id=2, name="Plant 2", photo_url="photos/2.jpg")
    ]
    db_session.query.return_value.filter.return_value.all.return_value = mock_plants
    
    # Act
    response = client.get("/my_plants/")
    
    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Plant 1"
    assert response.json()[1]["name"] == "Plant 2"
    assert "localhost:8000/photos/1.jpg" in response.json()[0]["photo_url"]

def test_list_other_plants(db_session, override_auth_regular_user):
    """Test listing all plants except user's."""
    # Arrange
    mock_plants = [
        Plant(id=3, name="Other Plant 1", photo_url="photos/3.jpg"),
        Plant(id=4, name="Other Plant 2", photo_url="photos/4.jpg")
    ]
    db_session.query.return_value.filter.return_value.all.return_value = mock_plants
    
    # Act
    response = client.get("/all_plants/")
    
    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Other Plant 1"
    assert response.json()[1]["name"] == "Other Plant 2"
    assert "localhost:8000/photos/3.jpg" in response.json()[0]["photo_url"]

# ======= PLANT CARE TESTS =======

def test_start_plant_care_success(db_session, override_auth_regular_user, mock_plant):
    """Test successful start of plant care."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = mock_plant
    
    # Act
    response = client.put(f"/plants/{mock_plant.id}/start-care")
    
    # Assert
    assert response.status_code == 200
    assert mock_plant.in_care == True
    db_session.commit.assert_called_once()

def test_start_plant_care_not_found(db_session, override_auth_regular_user):
    """Test starting care for non-existent plant returns 404."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = None
    
    # Act
    response = client.put("/plants/999/start-care")
    
    # Assert
    assert response.status_code == 404
    assert "Plant not found" in response.json()["detail"]

def test_end_plant_care_success(db_session, override_auth_regular_user, mock_plant):
    """Test successful end of plant care."""
    # Arrange
    mock_plant.in_care = True
    mock_plant.plant_sitting = 2
    db_session.query.return_value.filter.return_value.first.return_value = mock_plant
    
    # Act
    response = client.put(f"/plants/{mock_plant.id}/end-care")
    
    # Assert
    assert response.status_code == 200
    assert mock_plant.in_care == False
    assert mock_plant.plant_sitting is None
    db_session.commit.assert_called_once()

def test_end_plant_care_not_found(db_session, override_auth_regular_user):
    """Test ending care for non-existent plant returns 404."""
    # Arrange
    db_session.query.return_value.filter.return_value.first.return_value = None
    
    # Act
    response = client.put("/plants/999/end-care")
    
    # Assert
    assert response.status_code == 404
    assert "Plant not found" in response.json()["detail"]

def test_list_care_requests(db_session, override_auth_regular_user):
    """Test listing care requests."""
    # Arrange
    mock_plants_in_care = [
        Plant(id=5, name="Plant in Care 1", in_care=True, photo_url="photos/5.jpg", owner_id=2),
        Plant(id=6, name="Plant in Care 2", in_care=True, photo_url="photos/6.jpg", owner_id=3)
    ]
    db_session.query.return_value.filter.return_value.filter.return_value.all.return_value = mock_plants_in_care
    
    # Act
    response = client.get("/care-requests/")
    
    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Plant in Care 1"
    assert response.json()[1]["name"] == "Plant in Care 2"
    assert response.json()[0]["in_care"] == True
    assert "localhost:8000/photos/5.jpg" in response.json()[0]["photo_url"]