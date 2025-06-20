"""
Module d'observabilité corrigé pour Plant Care API
Supprime l'erreur AttributeError avec prometheus_fastapi_instrumentator
"""
import logging
import time
from typing import Optional
from contextlib import contextmanager
from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
import structlog

# Variables globales pour les métriques personnalisées
user_registrations_counter = None
plant_creations_counter = None
care_requests_counter = None
comments_counter = None
active_users_gauge = None
plants_in_care_gauge = None

class ObservabilityManager:
    """Gestionnaire d'observabilité simplifié et corrigé"""

    def __init__(self):
        self.instrumentator: Optional[Instrumentator] = None
        self.logger = structlog.get_logger()
        self.current_user_id: Optional[str] = None

    def initialize(self, app: FastAPI):
        """Initialise l'observabilité pour l'application"""
        try:
            print("Initializing observability stack...")
            self.setup_logging()
            self.setup_metrics(app)
            self.setup_custom_metrics()
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
        """Configure les métriques Prometheus - VERSION CORRIGÉE"""
        try:
            # Utiliser une configuration simplifiée de l'instrumentator
            self.instrumentator = Instrumentator(
                should_group_status_codes=False,
                should_ignore_untemplated=True,
                should_respect_env_var=True,
                should_instrument_requests_inprogress=True,
                excluded_handlers=[".*admin.*", "/metrics"],
                env_var_name="ENABLE_METRICS",
                inprogress_name="http_requests_inprogress",
                inprogress_labels=True,
            )

            # Instrumenter l'application
            self.instrumentator.instrument(app)

            # Exposer les métriques sur /metrics
            self.instrumentator.expose(app, endpoint="/metrics")

            print("Prometheus metrics configured successfully")

        except Exception as e:
            print(f"Warning: Could not setup Prometheus metrics: {e}")
            # Ajouter un endpoint de métriques basique
            @app.get("/metrics")
            async def basic_metrics():
                return {"status": "metrics_unavailable", "message": str(e)}

    def setup_custom_metrics(self):
        """Configure les métriques personnalisées pour l'application"""
        global user_registrations_counter, plant_creations_counter, care_requests_counter
        global comments_counter, active_users_gauge, plants_in_care_gauge

        try:
            # Compteurs pour les événements business
            user_registrations_counter = Counter(
                'plant_care_user_registrations_total',
                'Number of user registrations',
                ['user_type']
            )

            plant_creations_counter = Counter(
                'plant_care_plant_creations_total',
                'Number of plants created',
                ['owner_type']
            )

            care_requests_counter = Counter(
                'plant_care_care_requests_total',
                'Number of care requests',
                ['action']
            )

            comments_counter = Counter(
                'plant_care_comments_created_total',
                'Number of comments created'
            )

            # Gauges pour les valeurs courantes
            active_users_gauge = Gauge(
                'plant_care_active_users',
                'Number of currently active users'
            )

            plants_in_care_gauge = Gauge(
                'plant_care_plants_in_care',
                'Number of plants currently in care'
            )

            print("Custom metrics configured successfully")

        except Exception as e:
            print(f"Warning: Could not setup custom metrics: {e}")

    def setup_middleware(self, app: FastAPI):
        """Configure les middlewares d'observabilité"""

        @app.middleware("http")
        async def logging_middleware(request: Request, call_next):
            start_time = time.time()

            # Log de la requête entrante avec contexte utilisateur
            user_context = {"user_id": self.current_user_id} if self.current_user_id else {}

            self.logger.info(
                "request_started",
                method=request.method,
                url=str(request.url),
                client_ip=request.client.host if request.client else "unknown",
                **user_context
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
                    process_time=f"{process_time:.4f}s",
                    **user_context
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
                    process_time=f"{process_time:.4f}s",
                    **user_context
                )
                raise

    # Méthodes pour enregistrer les métriques business
    def record_user_registration(self, user_type: str = "regular"):
        """Enregistre une inscription d'utilisateur"""
        try:
            if user_registrations_counter:
                user_registrations_counter.labels(user_type=user_type).inc()
        except Exception as e:
            print(f"Error recording user registration metric: {e}")

    def record_plant_creation(self, owner_type: str = "regular"):
        """Enregistre la création d'une plante"""
        try:
            if plant_creations_counter:
                plant_creations_counter.labels(owner_type=owner_type).inc()
        except Exception as e:
            print(f"Error recording plant creation metric: {e}")

    def record_care_request(self, action: str):
        """Enregistre une demande de soin"""
        try:
            if care_requests_counter:
                care_requests_counter.labels(action=action).inc()
        except Exception as e:
            print(f"Error recording care request metric: {e}")

    def record_comment_creation(self):
        """Enregistre la création d'un commentaire"""
        try:
            if comments_counter:
                comments_counter.inc()
        except Exception as e:
            print(f"Error recording comment creation metric: {e}")

    def update_active_users(self, count: int):
        """Met à jour le nombre d'utilisateurs actifs"""
        try:
            if active_users_gauge:
                active_users_gauge.set(count)
        except Exception as e:
            print(f"Error updating active users metric: {e}")

    def update_plants_in_care(self, count: int):
        """Met à jour le nombre de plantes en soin"""
        try:
            if plants_in_care_gauge:
                plants_in_care_gauge.set(count)
        except Exception as e:
            print(f"Error updating plants in care metric: {e}")

    # Gestion du contexte utilisateur
    def set_current_user(self, user_id: str):
        """Définit l'utilisateur courant pour le contexte"""
        self.current_user_id = user_id

    def clear_current_user(self):
        """Efface l'utilisateur courant du contexte"""
        self.current_user_id = None

    @contextmanager
    def user_context(self, user_id: str):
        """Context manager pour définir temporairement un utilisateur"""
        old_user = self.current_user_id
        self.set_current_user(user_id)
        try:
            yield
        finally:
            if old_user:
                self.set_current_user(old_user)
            else:
                self.clear_current_user()

    # Méthodes de logging avec contexte
    def log_info(self, message: str, **kwargs):
        """Log d'information avec contexte utilisateur"""
        try:
            if self.current_user_id:
                kwargs["user_id"] = self.current_user_id
            self.logger.info(message, **kwargs)
        except:
            print(f"INFO: {message} - {kwargs}")

    def log_error(self, message: str, **kwargs):
        """Log d'erreur avec contexte utilisateur"""
        try:
            if self.current_user_id:
                kwargs["user_id"] = self.current_user_id
            self.logger.error(message, **kwargs)
        except:
            print(f"ERROR: {message} - {kwargs}")

    def log_warning(self, message: str, **kwargs):
        """Log d'avertissement avec contexte utilisateur"""
        try:
            if self.current_user_id:
                kwargs["user_id"] = self.current_user_id
            self.logger.warning(message, **kwargs)
        except:
            print(f"WARNING: {message} - {kwargs}")

# Instance globale
observability = ObservabilityManager()

# Fonctions de commodité pour maintenir la compatibilité
def get_logger():
    """Retourne le logger structuré"""
    return observability.logger

def get_tracer():
    """Retourne None car on n'utilise pas OpenTelemetry tracing dans cette version simplifiée"""
    return None

def trace_function(name: str):
    """Décorateur factice pour maintenir la compatibilité"""
    def decorator(func):
        return func
    return decorator