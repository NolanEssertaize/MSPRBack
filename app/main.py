import os
import fastapi.responses
from datetime import datetime as dt
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
import time
from app import models
from app.database import engine
from app.observability import observability, get_logger, get_tracer

from app.routers import auth as auth_routes
from app.routers import users as users_routes
from app.routers import plants as plants_routes
from app.routers import comments as comments_routes

base_url = "localhost:8000"
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="A_rosa_je API",
    description="Plant Care Application with LGTM Observability Stack",
    version="1.0.0"
)

observability.initialize(app)
logger = get_logger()
tracer = get_tracer()

os.makedirs("photos", exist_ok=True)

app.mount("/photos", StaticFiles(directory="photos"), name="photos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    
    start_time = time.time()

    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            observability.set_current_user("authenticated_user")
        except:
            pass

    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        user_agent=request.headers.get("user-agent"),
        client_ip=request.client.host
    )

    span_context = None
    if tracer is not None:
        try:
            span_context = tracer.start_as_current_span(
                f"{request.method} {request.url.path}",
                attributes={
                    "http.method": request.method,
                    "http.url": str(request.url),
                    "http.user_agent": request.headers.get("user-agent", ""),
                    "http.client_ip": request.client.host,
                }
            )
        except Exception as e:
            logger.warning(f"Could not start tracing span: {e}")
            span_context = None

    try:
        if span_context is not None:
            with span_context:
                response = await call_next(request)
        else:
            response = await call_next(request)

        duration = time.time() - start_time

        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2)
        )

        return response

    except Exception as e:
        duration = time.time() - start_time

        logger.error(
            "Request failed",
            method=request.method,
            url=str(request.url),
            error=str(e),
            duration_ms=round(duration * 1000, 2)
        )
        raise
    finally:
        observability.clear_current_user()

@app.get("/health")
async def health_check():
    
    return {
        "status": "healthy",
        "timestamp": dt.utcnow().isoformat(),
        "service": "plant-care-api",
        "version": "1.0.0"
    }

@app.options("/{rest_of_path:path}")
async def preflight_handler():
    response = fastapi.responses.Response(status_code=204)
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:5000"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

app.include_router(auth_routes.router)
app.include_router(users_routes.router)
app.include_router(plants_routes.router)
app.include_router(comments_routes.router)
