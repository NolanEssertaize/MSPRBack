# app/config.py (updated)
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./a_rosa_je.db"
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Configuration du chiffrement
    ENCRYPTION_KEY: str = "plant-care-encryption-default-key-change-this-in-production"
    ENCRYPTION_ENABLED: bool = True
    
    # Configuration de test
    TESTING: bool = False
    TEST_DATABASE_URL: str = "sqlite:///./test_a_rosa_je.db"

    class Config:
        env_file = ".env"


# Charger les variables d'environnement
settings = Settings()

# Pour les tests, utiliser la base de données de test
if os.getenv("TESTING", "").lower() in ("true", "1", "t"):
    settings.TESTING = True
    settings.DATABASE_URL = settings.TEST_DATABASE_URL