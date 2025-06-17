"""
Module d'observabilité corrigé pour Plant Care API
"""
import logging
import time
from typing import Optional
from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
import structlog

class ObservabilityManager:
    """Gestionnaire d'observabilité simplifié"""

    def __init__(self):
        self.instrumentator: Optional[Instrumentator] = None
        self.logger = structlog.get_logger()

    def initialize(self, app: FastAPI):
        """Initialise l'observabilité pour l'application"""
        try:
            print("Initializing observability stack...")
            self.setup_logging()
            self.setup_metrics(app)
            self.setup_middleware(app)
            print("Observability stack initialized successfully!")

        except Exception as e:
            print(f"Warning: Could not initialize full observability stack: {e}")
            print("Continuing with basic logging only...")
            self.setup_basic_logging()

    def setup_logging(self):
        """Configure le logging structuré"""
        try:
            structlog.configure(
                processors=[
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.add_log_level,
                    structlog.processors.JSONRenderer()
                ],
                wrapper_class=structlog.make_filtering_bound_logger(30),  # INFO level
                logger_factory=structlog.PrintLoggerFactory(),
                cache_logger_on_first_use=True,
            )
        except Exception as e:
            print(f"Warning: Could not setup structured logging: {e}")
            self.setup_basic_logging()

    def setup_basic_logging(self):
        """Configure un logging basique en cas d'échec"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def setup_metrics(self, app: FastAPI):
        """Configure les métriques Prometheus"""
        try:
            # Utiliser une configuration simplifiée de l'instrumentator
            self.instrumentator = Instrumentator()
            self.instrumentator.instrument(app)
            self.instrumentator.expose(app, endpoint="/metrics")
            print("Prometheus metrics configured successfully")

        except Exception as e:
            print(f"Warning: Could not setup Prometheus metrics: {e}")
            # Ajouter un endpoint de métriques basique
            @app.get("/metrics")
            async def basic_metrics():
                return {"status": "metrics_unavailable", "message": str(e)}

    def setup_middleware(self, app: FastAPI):
        """Configure les middlewares d'observabilité"""

        @app.middleware("http")
        async def logging_middleware(request: Request, call_next):
            start_time = time.time()

            # Log de la requête entrante
            self.logger.info(
                "request_started",
                method=request.method,
                url=str(request.url),
                client_ip=request.client.host if request.client else "unknown"
            )

            try:
                response = await call_next(request)

                # Calculer le temps de traitement
                process_time = time.time() - start_time

                # Log de la réponse
                self.logger.info(
                    "request_completed",
                    method=request.method,
                    url=str(request.url),
                    status_code=response.status_code,
                    process_time=f"{process_time:.4f}s"
                )

                # Ajouter le header de temps de traitement
                response.headers["X-Process-Time"] = str(process_time)
                return response

            except Exception as e:
                process_time = time.time() - start_time

                # Log de l'erreur
                self.logger.error(
                    "request_failed",
                    method=request.method,
                    url=str(request.url),
                    error=str(e),
                    process_time=f"{process_time:.4f}s"
                )
                raise

    def log_info(self, message: str, **kwargs):
        """Log d'information"""
        try:
            self.logger.info(message, **kwargs)
        except:
            print(f"INFO: {message} - {kwargs}")

    def log_error(self, message: str, **kwargs):
        """Log d'erreur"""
        try:
            self.logger.error(message, **kwargs)
        except:
            print(f"ERROR: {message} - {kwargs}")

    def log_warning(self, message: str, **kwargs):
        """Log d'avertissement"""
        try:
            self.logger.warning(message, **kwargs)
        except:
            print(f"WARNING: {message} - {kwargs}")

# Instance globale
observability = ObservabilityManager()