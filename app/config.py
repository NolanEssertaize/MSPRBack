import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    DATABASE_URL: str = "postgresql://plant_user:plant_password@localhost:5432/plant_care_db"

    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    ENCRYPTION_KEY: str = "plant-care-encryption-default-key-change-this-in-production"
    ENCRYPTION_ENABLED: bool = True

    TESTING: bool = False
    TEST_DATABASE_URL: str = "postgresql://plant_user:plant_password@localhost:5432/plant_care_test_db"

    ENABLE_OBSERVABILITY: bool = True
    OTEL_SERVICE_NAME: str = "plant-care-api"
    OTEL_SERVICE_VERSION: str = "1.0.0"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://alloy:4317"
    OTEL_RESOURCE_ATTRIBUTES: str = "service.name=plant-care-api,service.version=1.0.0"

    ENABLE_METRICS: bool = True
    METRICS_EXPORT_INTERVAL: int = 15  # secondes

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json ou text

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300  # 5 minutes

    UPLOAD_DIRECTORY: str = "photos"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: list = ["jpg", "jpeg", "png", "gif"]

    CORS_ORIGINS: list = ["http://localhost:5000", "http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True

    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # secondes

    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

if os.getenv("TESTING", "").lower() in ("true", "1", "t"):
    settings.TESTING = True
    settings.DATABASE_URL = settings.TEST_DATABASE_URL
    settings.ENABLE_OBSERVABILITY = False  # Désactiver pour les tests
    settings.DEBUG = True

if settings.ENVIRONMENT == "production":
    settings.DEBUG = False
    settings.LOG_LEVEL = "WARNING"

    if settings.SECRET_KEY == "your-secret-key":
        raise ValueError("SECRET_KEY must be configured in production")
    if "default-key" in settings.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY must be configured in production")

def get_database_url() -> str:
    
    if settings.TESTING:
        return settings.TEST_DATABASE_URL
    return settings.DATABASE_URL

def get_log_config() -> dict:
    
    if settings.LOG_FORMAT == "json":
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": "ext://sys.stdout"
                }
            },
            "root": {
                "level": settings.LOG_LEVEL,
                "handlers": ["console"]
            }
        }
    else:
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "stream": "ext://sys.stdout"
                }
            },
            "root": {
                "level": settings.LOG_LEVEL,
                "handlers": ["console"]
            }
        }

def validate_config():
    
    errors = []

    if not settings.SECRET_KEY:
        errors.append("SECRET_KEY is required")

    if not settings.ENCRYPTION_KEY:
        errors.append("ENCRYPTION_KEY is required")

    if not settings.DATABASE_URL:
        errors.append("DATABASE_URL is required")

    if settings.ENABLE_OBSERVABILITY and not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        errors.append("OTEL_EXPORTER_OTLP_ENDPOINT is required when observability is enabled")

    if not os.path.exists(settings.UPLOAD_DIRECTORY):
        try:
            os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create upload directory {settings.UPLOAD_DIRECTORY}: {e}")

    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")

if not settings.TESTING:
    validate_config()
