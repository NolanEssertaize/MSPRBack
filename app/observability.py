# app/observability.py
"""
Module d'observabilité pour l'application Plant Care
Intègre la stack LGTM (Loki, Grafana, Tempo, Mimir) avec OpenTelemetry
"""

import os
import logging
import structlog
from typing import Any, Dict
from contextvars import ContextVar
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator, metrics

# Variables de contexte pour le tracing
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')
span_id_var: ContextVar[str] = ContextVar('span_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')

class PlantCareObservability:
    """Classe principale pour gérer l'observabilité de l'application"""

    def __init__(self):
        self.tracer = None
        self.meter = None
        self.logger = None
        self.metrics = {}
        self.is_initialized = False

    def setup_resource(self) -> Resource:
        """Configure la resource OpenTelemetry avec les métadonnées du service"""
        return Resource.create({
            "service.name": os.getenv("OTEL_SERVICE_NAME", "plant-care-api"),
            "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
            "service.namespace": os.getenv("SERVICE_NAMESPACE", "production"),
            "service.instance.id": os.getenv("HOSTNAME", "unknown"),
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
        })

    def setup_tracing(self):
        """Configure le tracing avec OpenTelemetry et export vers Tempo"""
        resource = self.setup_resource()

        # Configurer le TracerProvider
        trace.set_tracer_provider(TracerProvider(resource=resource))

        # Configurer l'exporteur OTLP pour Tempo
        otlp_exporter = OTLPSpanExporter(
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://alloy:4317"),
            insecure=True
        )

        # Ajouter le processeur de spans
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)

        # Obtenir le tracer
        self.tracer = trace.get_tracer(__name__)

    def setup_metrics(self):
        """Configure les métriques avec OpenTelemetry et export vers Mimir"""
        resource = self.setup_resource()

        # Configurer l'exporteur OTLP pour les métriques
        metric_exporter = OTLPMetricExporter(
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://alloy:4317"),
            insecure=True
        )

        # Configurer le reader avec export périodique
        metric_reader = PeriodicExportingMetricReader(
            exporter=metric_exporter,
            export_interval_millis=15000  # 15 secondes
        )

        # Configurer le MeterProvider
        metrics.set_meter_provider(
            MeterProvider(
                resource=resource,
                metric_readers=[metric_reader]
            )
        )

        # Obtenir le meter
        self.meter = metrics.get_meter(__name__)

        # Créer les métriques custom
        self.setup_custom_metrics()

    def setup_custom_metrics(self):
        """Configure les métriques custom de l'application"""
        # Compteurs
        self.metrics['user_registrations'] = self.meter.create_counter(
            name="plant_care_user_registrations_total",
            description="Total number of user registrations"
        )

        self.metrics['plant_creations'] = self.meter.create_counter(
            name="plant_care_plant_creations_total",
            description="Total number of plants created"
        )

        self.metrics['care_requests'] = self.meter.create_counter(
            name="plant_care_care_requests_total",
            description="Total number of care requests"
        )

        self.metrics['comments_created'] = self.meter.create_counter(
            name="plant_care_comments_created_total",
            description="Total number of comments created"
        )

        # Gauges
        self.metrics['active_users'] = self.meter.create_up_down_counter(
            name="plant_care_active_users",
            description="Number of currently active users"
        )

        self.metrics['plants_in_care'] = self.meter.create_up_down_counter(
            name="plant_care_plants_in_care",
            description="Number of plants currently in care"
        )

        # Histogrammes
        self.metrics['request_duration'] = self.meter.create_histogram(
            name="plant_care_request_duration_seconds",
            description="Request duration in seconds"
        )

        self.metrics['database_query_duration'] = self.meter.create_histogram(
            name="plant_care_database_query_duration_seconds",
            description="Database query duration in seconds"
        )

    def setup_logging(self):
        """Configure le logging structuré avec intégration de tracing"""
        # Configurer structlog
        structlog.configure(
            processors=[
                self._add_trace_info,
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Configurer le logger standard
        logging.basicConfig(
            format="%(message)s",
            level=logging.INFO,
        )

        self.logger = structlog.get_logger("plant_care")

    def _add_trace_info(self, logger, method_name, event_dict):
        """Ajoute les informations de tracing aux logs"""
        span = trace.get_current_span()
        if span != trace.INVALID_SPAN:
            span_context = span.get_span_context()
            event_dict["trace_id"] = format(span_context.trace_id, "032x")
            event_dict["span_id"] = format(span_context.span_id, "016x")

        # Ajouter l'ID utilisateur si disponible
        user_id = user_id_var.get('')
        if user_id:
            event_dict["user_id"] = user_id

        return event_dict

    def setup_instrumentations(self, app):
        """Configure les instrumentations automatiques"""
        # Instrumentation FastAPI
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=trace.get_tracer_provider(),
            excluded_urls="/health,/metrics,/docs,/openapi.json"
        )

        # Instrumentation SQLAlchemy
        SQLAlchemyInstrumentor().instrument()

        # Instrumentation PostgreSQL
        Psycopg2Instrumentor().instrument()

        # Instrumentation des requêtes HTTP
        RequestsInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()

    def setup_prometheus_metrics(self, app):
        """Configure les métriques Prometheus pour FastAPI"""
        instrumentator = Instrumentator(
            should_group_status_codes=False,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/health", "/metrics", "/docs", "/openapi.json"],
            env_var_name="ENABLE_METRICS",
            inprogress_name="plant_care_requests_inprogress",
            inprogress_labels=True,
        )

        # Ajouter des métriques custom
        instrumentator.add(
            metrics.request_size(
                should_include_handler=True,
                should_include_method=True,
                should_include_status=True,
                metric_name="plant_care_request_size_bytes",
                metric_doc="Size of requests in bytes",
            )
        ).add(
            metrics.response_size(
                should_include_handler=True,
                should_include_method=True,
                should_include_status=True,
                metric_name="plant_care_response_size_bytes",
                metric_doc="Size of responses in bytes",
            )
        ).add(
            metrics.latency(
                should_include_handler=True,
                should_include_method=True,
                should_include_status=True,
                metric_name="plant_care_request_duration_seconds",
                metric_doc="Duration of requests in seconds",
            )
        )

        # Instrumenter l'application
        instrumentator.instrument(app)
        instrumentator.expose(app, endpoint="/metrics")

        return instrumentator

    def initialize(self, app):
        """Initialise tous les composants d'observabilité"""
        if self.is_initialized:
            return

        # Vérifier si l'observabilité est activée
        if os.getenv("ENABLE_OBSERVABILITY", "true").lower() not in ("true", "1"):
            print("Observability disabled")
            return

        print("Initializing observability stack...")

        # Setup des composants
        self.setup_tracing()
        self.setup_metrics()
        self.setup_logging()
        self.setup_instrumentations(app)
        self.setup_prometheus_metrics(app)

        self.is_initialized = True
        self.logger.info("Observability stack initialized successfully")

    def record_user_registration(self, user_type: str = "regular"):
        """Enregistre une métrique de registration d'utilisateur"""
        if self.metrics.get('user_registrations'):
            self.metrics['user_registrations'].add(1, {"user_type": user_type})

    def record_plant_creation(self, owner_type: str = "regular"):
        """Enregistre une métrique de création de plante"""
        if self.metrics.get('plant_creations'):
            self.metrics['plant_creations'].add(1, {"owner_type": owner_type})

    def record_care_request(self, action: str = "start"):
        """Enregistre une métrique de demande de soin"""
        if self.metrics.get('care_requests'):
            self.metrics['care_requests'].add(1, {"action": action})

    def record_comment_creation(self, comment_type: str = "regular"):
        """Enregistre une métrique de création de commentaire"""
        if self.metrics.get('comments_created'):
            self.metrics['comments_created'].add(1, {"comment_type": comment_type})

    def set_current_user(self, user_id: str):
        """Définit l'utilisateur courant pour le contexte de tracing"""
        user_id_var.set(user_id)

    def clear_current_user(self):
        """Nettoie l'utilisateur courant du contexte"""
        user_id_var.set('')

    def get_tracer(self):
        """Retourne le tracer OpenTelemetry"""
        return self.tracer

    def get_logger(self):
        """Retourne le logger structuré"""
        return self.logger

    def record_database_query(self, query_type: str, duration: float):
        """Enregistre une métrique de requête base de données"""
        if self.metrics.get('database_query_duration'):
            self.metrics['database_query_duration'].record(
                duration,
                {"query_type": query_type}
            )

# Instance globale
observability = PlantCareObservability()

# Fonctions utilitaires
def get_tracer():
    """Fonction utilitaire pour obtenir le tracer"""
    return observability.get_tracer()

def get_logger():
    """Fonction utilitaire pour obtenir le logger"""
    return observability.get_logger()

def trace_function(operation_name: str):
    """Décorateur pour tracer automatiquement les fonctions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if tracer:
                with tracer.start_as_current_span(operation_name):
                    return func(*args, **kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def record_custom_metric(metric_name: str, value: float, attributes: Dict[str, Any] = None):
    """Enregistre une métrique custom"""
    if observability.metrics.get(metric_name):
        observability.metrics[metric_name].record(value, attributes or {})