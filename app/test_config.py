# app/test_config.py
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import get_db, Base
from app import models
from app.auth import get_current_user, create_access_token, get_password_hash
from datetime import timedelta
from app.config import settings

# Configuration de la base de données de test (en mémoire)
TEST_DATABASE_URL = "sqlite:///./test_a_rosa_je.db"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def get_test_db():
    """Fournit une session de base de données de test."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Client de test
test_client = TestClient(app)

@pytest.fixture(scope="session")
def initialize_test_db():
    """Initialise la base de données de test une fois pour l'ensemble de la session."""
    # Créer toutes les tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Supprimer le fichier de base de données après les tests
    if os.path.exists("./test_a_rosa_je.db"):
        os.remove("./test_a_rosa_je.db")

@pytest.fixture(scope="function")
def db_session(initialize_test_db):
    """Fournit une session de base de données pour chaque test."""
    # Connecter à la base de données
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    
    # Remplacer la dépendance get_db dans l'application
    app.dependency_overrides[get_db] = lambda: session
    
    yield session
    
    # Nettoyer après le test
    session.close()
    transaction.rollback()
    connection.close()

def create_test_user(db_session, is_botanist=False):
    """Crée un utilisateur de test dans la base de données."""
    hashed_password = get_password_hash("testpassword")
    test_user = models.User(
        username="testuser",
        email="test@example.com",
        phone="123456789",
        hashed_password=hashed_password,
        is_botanist=is_botanist
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)
    return test_user

def create_test_botanist(db_session):
    """Crée un botaniste de test dans la base de données."""
    return create_test_user(db_session, is_botanist=True)

def create_test_plant(db_session, owner_id):
    """Crée une plante de test dans la base de données."""
    test_plant = models.Plant(
        name="Test Plant",
        location="Living Room",
        care_instructions="Water once a week",
        owner_id=owner_id
    )
    db_session.add(test_plant)
    db_session.commit()
    db_session.refresh(test_plant)
    return test_plant

def get_test_token(user):
    """Crée un token JWT pour un utilisateur de test."""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return access_token

@pytest.fixture
def authenticated_client(db_session):
    """Fournit un client de test avec un utilisateur authentifié."""
    # Créer un utilisateur de test
    test_user = create_test_user(db_session)
    
    # Créer un token pour cet utilisateur
    token = get_test_token(test_user)
    
    # Configurer la dépendance d'authentification
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    # Créer un client avec le token dans les headers
    client = TestClient(app)
    client.headers = {"Authorization": f"Bearer {token}"}
    
    return client, test_user

@pytest.fixture
def authenticated_botanist_client(db_session):
    """Fournit un client de test avec un botaniste authentifié."""
    # Créer un botaniste de test
    test_botanist = create_test_botanist(db_session)
    
    # Créer un token pour ce botaniste
    token = get_test_token(test_botanist)
    
    # Configurer la dépendance d'authentification
    app.dependency_overrides[get_current_user] = lambda: test_botanist
    
    # Créer un client avec le token dans les headers
    client = TestClient(app)
    client.headers = {"Authorization": f"Bearer {token}"}
    
    return client, test_botanist

def cleanup_test_files():
    """Nettoie les fichiers créés pendant les tests."""
    # Supprimer les photos de test
    test_photos_dir = "photos"
    if os.path.exists(test_photos_dir):
        for file in os.listdir(test_photos_dir):
            if file.startswith("test_"):
                os.remove(os.path.join(test_photos_dir, file))