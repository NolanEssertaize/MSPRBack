import os
import fastapi.responses
from datetime import datetime as dt
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta
import time
from app import schemas, auth, models
from app.security import security_manager
from app.database import engine, get_db
from app.config import settings
from app.observability import observability, get_logger, get_tracer, trace_function

# Initialiser l'observabilité avant l'application
base_url = "localhost:8000"
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="A_rosa_je API",
    description="Plant Care Application with LGTM Observability Stack",
    version="1.0.0"
)

# Initialiser l'observabilité
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

# Middleware pour l'observabilité
@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """Middleware pour ajouter des informations d'observabilité"""
    start_time = time.time()

    # Obtenir l'utilisateur courant s'il est authentifié
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            # Extraire l'ID utilisateur du token (simplifié)
            # En production, vous voudriez décoder le token proprement
            observability.set_current_user("authenticated_user")
        except:
            pass

    # Logger de la requête entrante
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        user_agent=request.headers.get("user-agent"),
        client_ip=request.client.host
    )

    # Tracer la requête
    with tracer.start_as_current_span(
            f"{request.method} {request.url.path}",
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.user_agent": request.headers.get("user-agent", ""),
                "http.client_ip": request.client.host,
            }
    ) if tracer else None:

        response = await call_next(request)

        # Calculer la durée
        duration = time.time() - start_time

        # Logger de la réponse
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2)
        )

        # Nettoyer le contexte utilisateur
        observability.clear_current_user()

        return response

@app.get("/health")
async def health_check():
    """Health check endpoint pour Kubernetes/Docker"""
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

# ======= AUTHENTICATION =======

@app.post("/token", tags=["Authentication"])
@trace_function("user_authentication")
async def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authentifie un utilisateur et renvoie un jeton JWT.
    """
    logger.info("User login attempt", email=form_data.username)

    # Recherchons l'utilisateur par son email en utilisant le hash
    email_hash = security_manager.hash_value(form_data.username)
    user = db.query(models.User).filter(models.User.email_hash == email_hash).first()

    # Vérifions si l'utilisateur existe et si le mot de passe est correct
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        logger.warning("Failed login attempt", email=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Générons le jeton d'accès avec l'email déchiffré comme identifiant
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": security_manager.decrypt_value(user.email_encrypted)},
        expires_delta=access_token_expires
    )

    logger.info("User login successful", user_id=user.id, is_botanist=user.is_botanist)
    observability.set_current_user(str(user.id))

    return {"access_token": access_token, "token_type": "bearer"}

# ======= USER MANAGEMENT =======

@app.post("/users/", response_model=schemas.User, tags=["Users"])
@trace_function("user_creation")
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Créer un nouvel utilisateur avec hashage et chiffrement des données sensibles"""

    logger.info("Creating new user", email=user.email, username=user.username, is_botanist=user.is_botanist)

    # Vérifier l'unicité de l'email en utilisant le hash
    email_hash = security_manager.hash_value(user.email)
    db_user = db.query(models.User).filter(models.User.email_hash == email_hash).first()
    if db_user:
        logger.warning("User creation failed - email already exists", email=user.email)
        raise HTTPException(status_code=400, detail="Email already registered")

    # Vérifier l'unicité du nom d'utilisateur en utilisant le hash
    username_hash = security_manager.hash_value(user.username)
    db_user = db.query(models.User).filter(models.User.username_hash == username_hash).first()
    if db_user:
        logger.warning("User creation failed - username already exists", username=user.username)
        raise HTTPException(status_code=400, detail="Username already taken")

    # Créer l'utilisateur avec versions hashées et chiffrées
    db_user = models.User(
        email_hash=email_hash,
        username_hash=username_hash,
        phone_hash=security_manager.hash_value(user.phone),
        email_encrypted=security_manager.encrypt_value(user.email),
        username_encrypted=security_manager.encrypt_value(user.username),
        phone_encrypted=security_manager.encrypt_value(user.phone),
        hashed_password=auth.get_password_hash(user.password),
        is_botanist=user.is_botanist,
        is_active=True
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Enregistrer la métrique
    user_type = "botanist" if user.is_botanist else "regular"
    observability.record_user_registration(user_type)

    logger.info("User created successfully", user_id=db_user.id, user_type=user_type)

    # Transformer le modèle DB en schéma de réponse avec les valeurs déchiffrées
    return {
        "id": db_user.id,
        "email": security_manager.decrypt_value(db_user.email_encrypted),
        "username": security_manager.decrypt_value(db_user.username_encrypted),
        "phone": security_manager.decrypt_value(db_user.phone_encrypted),
        "is_active": db_user.is_active,
        "is_botanist": db_user.is_botanist
    }

@app.put("/users/{user_id}", response_model=schemas.User, tags=["Users"])
@trace_function("user_update")
async def edit_user(
        user_id: int,
        email: EmailStr = None,
        username: str = None,
        phone: str = None,
        is_botanist: bool = None,
        current_user: schemas.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """Met à jour un compte utilisateur existant."""

    logger.info("Updating user", user_id=user_id, current_user_id=current_user.id)

    # Vérifier si l'utilisateur essaie de mettre à jour le profil de quelqu'un d'autre
    if user_id != current_user.id:
        logger.warning("Unauthorized user update attempt",
                       target_user_id=user_id,
                       current_user_id=current_user.id)
        raise HTTPException(status_code=403, detail="Not authorized to update other users")

    # Récupérer l'utilisateur à mettre à jour
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        logger.error("User not found for update", user_id=user_id)
        raise HTTPException(status_code=404, detail="User not found")

    # Vérifier l'unicité de l'email et du username si modifiés
    if email and email != current_user.email:
        email_hash = security_manager.hash_value(email)
        existing_user = db.query(models.User).filter(models.User.email_hash == email_hash).first()
        if existing_user and existing_user.id != user_id:
            logger.warning("Email already taken", email=email, user_id=user_id)
            raise HTTPException(status_code=400, detail="Email already registered")

    if username and username != current_user.username:
        username_hash = security_manager.hash_value(username)
        existing_user = db.query(models.User).filter(models.User.username_hash == username_hash).first()
        if existing_user and existing_user.id != user_id:
            logger.warning("Username already taken", username=username, user_id=user_id)
            raise HTTPException(status_code=400, detail="Username already taken")

    # Mettre à jour les champs
    if email is not None:
        db_user.email_hash = security_manager.hash_value(email)
        db_user.email_encrypted = security_manager.encrypt_value(email)
    if username is not None:
        db_user.username_hash = security_manager.hash_value(username)
        db_user.username_encrypted = security_manager.encrypt_value(username)
    if phone is not None:
        db_user.phone_hash = security_manager.hash_value(phone)
        db_user.phone_encrypted = security_manager.encrypt_value(phone)
    if is_botanist is not None:
        db_user.is_botanist = is_botanist

    db.commit()
    db.refresh(db_user)

    logger.info("User updated successfully", user_id=user_id)

    return {
        "id": db_user.id,
        "email": security_manager.decrypt_value(db_user.email_encrypted),
        "username": security_manager.decrypt_value(db_user.username_encrypted),
        "phone": security_manager.decrypt_value(db_user.phone_encrypted),
        "is_active": db_user.is_active,
        "is_botanist": db_user.is_botanist
    }

@app.get("/users/me/", tags=["Users"])
@trace_function("get_current_user")
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """Get details of the currently authenticated user."""
    logger.info("Getting current user details", user_id=current_user.id)
    return current_user

@app.delete("/users/", tags=["Users"])
@trace_function("user_deletion")
async def delete_user(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Delete a user account."""
    logger.info("Deleting user", user_id=id, current_user_id=current_user.id)

    db_user = db.query(models.User).filter(models.User.id == id).first()
    if not db_user:
        logger.error("User not found for deletion", user_id=id)
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()

    logger.info("User deleted successfully", user_id=id)
    return db_user

# ======= PLANT MANAGEMENT =======

@app.post("/plants/", tags=["Plants"])
@trace_function("plant_creation")
async def create_plant(
        name: str,
        location: str,
        care_instructions: str | None = None,
        photo: UploadFile = File(),
        current_user: models.User = Depends(auth.get_current_user),
        in_care_id: int = None,
        db: Session = Depends(get_db)
):
    """Create a new plant entry."""
    logger.info("Creating new plant",
                plant_name=name,
                location=location,
                owner_id=current_user.id)

    plant_data = {
        "name": name,
        "location": location,
        "care_instructions": care_instructions,
        "owner_id": current_user.id,
        "in_care_id": in_care_id
    }

    db_plant = models.Plant(**plant_data)
    if photo:
        photo_path = f"photos/{current_user.id}_{photo.filename}"
        with open(photo_path, "wb") as buffer:
            content = await photo.read()
            buffer.write(content)
        db_plant.photo_url = photo_path
        logger.info("Plant photo saved", photo_path=photo_path)

    db.add(db_plant)
    db.commit()
    db.refresh(db_plant)

    # Enregistrer la métrique
    owner_type = "botanist" if current_user.is_botanist else "regular"
    observability.record_plant_creation(owner_type)

    logger.info("Plant created successfully",
                plant_id=db_plant.id,
                owner_type=owner_type)

    return db_plant

@app.put("/plants/{plant_id}", tags=["Plants"])
@trace_function("plant_update")
async def update_plant(
        plant_id: int,
        name: str = None,
        location: str = None,
        care_instructions: str | None = None,
        photo: UploadFile = File(None),
        current_user: models.User = Depends(auth.get_current_user),
        in_care_id: int = None,
        db: Session = Depends(get_db)
):
    """Update an existing plant."""
    logger.info("Updating plant", plant_id=plant_id, user_id=current_user.id)

    plant = db.query(models.Plant).filter(
        models.Plant.id == plant_id,
        models.Plant.owner_id == current_user.id
    ).first()

    if plant is None:
        logger.error("Plant not found or not owned by user",
                     plant_id=plant_id,
                     user_id=current_user.id)
        raise HTTPException(
            status_code=404,
            detail="Plant not found or not owned by current user"
        )

    # Mettre à jour les champs
    if name is not None:
        plant.name = name
    if location is not None:
        plant.location = location
    if care_instructions is not None:
        plant.care_instructions = care_instructions
    if in_care_id is not None:
        plant.in_care_id = in_care_id

    if photo and photo.filename:
        # Supprimer l'ancienne photo
        if plant.photo_url and os.path.exists(plant.photo_url.replace(f"{base_url}/", "")):
            try:
                os.remove(plant.photo_url.replace(f"{base_url}/", ""))
            except Exception as e:
                logger.warning("Error removing old photo", error=str(e))

        photo_filename = f"{current_user.id}_{photo.filename}"
        photo_path = f"photos/{photo_filename}"

        with open(photo_path, "wb") as buffer:
            content = await photo.read()
            buffer.write(content)

        plant.photo_url = f"{base_url}/photos/{photo_filename}"
        logger.info("Plant photo updated", photo_path=photo_path)

    db.commit()
    db.refresh(plant)

    logger.info("Plant updated successfully", plant_id=plant_id)
    return plant

@app.delete("/plants", tags=["Plants"])
@trace_function("plant_deletion")
async def delete_plant(
        plant_id: int,
        db: Session = Depends(get_db)
):
    """Delete a plant."""
    logger.info("Deleting plant", plant_id=plant_id)

    plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    if not plant:
        logger.error("Plant not found for deletion", plant_id=plant_id)
        raise HTTPException(status_code=404, detail="The plant was not found")

    try:
        db.delete(plant)
        db.commit()
        logger.info("Plant deleted successfully", plant_id=plant_id)
        return plant
    except Exception as e:
        logger.error("Error deleting plant", plant_id=plant_id, error=str(e))
        raise HTTPException(status_code=500, detail="Error deleting plant")

@app.get("/my_plants/", tags=["Plants"])
@trace_function("list_user_plants")
async def list_plants_users_plant(
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """List all plants owned by the current user."""
    logger.info("Listing user plants", user_id=current_user.id)

    plants = db.query(models.Plant).filter(models.Plant.owner_id == current_user.id).all()
    for plant in plants:
        photofile = plant.photo_url
        if plant.photo_url:
            plant.photo_url = base_url + "/" + photofile

    logger.info("User plants retrieved", user_id=current_user.id, count=len(plants))
    return plants

@app.get("/all_plants/", tags=["Plants"])
@trace_function("list_all_plants")
async def list_all_plants_except_users(
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """List all plants except those owned by the current user."""
    logger.info("Listing all plants except user's", user_id=current_user.id)

    plants = db.query(models.Plant).filter(models.Plant.owner_id != current_user.id).all()
    for plant in plants:
        photofile = plant.photo_url
        if plant.photo_url:
            plant.photo_url = base_url + "/" + photofile

    logger.info("All plants retrieved", user_id=current_user.id, count=len(plants))
    return plants

# ======= PLANT CARE =======

@app.put("/plants/{plant_id}/start-care", tags=["Plant Care"])
@trace_function("start_plant_care")
async def start_plant_care(
        plant_id: int,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """Start plant care by assigning a botanist."""
    logger.info("Starting plant care", plant_id=plant_id, botanist_id=current_user.id)

    plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    if not plant:
        logger.error("Plant not found for care", plant_id=plant_id)
        raise HTTPException(status_code=404, detail="Plant not found")

    plant.in_care_id = current_user.id
    db.commit()
    db.refresh(plant)

    # Enregistrer la métrique
    observability.record_care_request("start")

    logger.info("Plant care started", plant_id=plant_id, botanist_id=current_user.id)
    return plant

@app.put("/plants/{plant_id}/end-care", tags=["Plant Care"])
@trace_function("end_plant_care")
async def end_plant_care(
        plant_id: int,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """End plant care."""
    logger.info("Ending plant care", plant_id=plant_id, botanist_id=current_user.id)

    plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    if not plant or plant.in_care_id != current_user.id:
        logger.error("Plant not found or not caring by user",
                     plant_id=plant_id,
                     user_id=current_user.id)
        raise HTTPException(status_code=404, detail="Plant not found or not caring by user")

    plant.in_care_id = None
    plant.plant_sitting = None
    db.commit()
    db.refresh(plant)

    # Enregistrer la métrique
    observability.record_care_request("end")

    logger.info("Plant care ended", plant_id=plant_id, botanist_id=current_user.id)
    return plant

@app.get("/care-requests/", tags=["Plant Care"])
@trace_function("list_care_requests")
async def list_care_requests(
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """List care requests."""
    logger.info("Listing care requests", user_id=current_user.id)

    care_requests = db.query(models.Plant).filter(
        models.Plant.in_care_id != None,
        models.Plant.owner_id != current_user.id
    ).all()

    for plant in care_requests:
        photofile = plant.photo_url
        if plant.photo_url:
            plant.photo_url = base_url + "/" + photofile

    logger.info("Care requests retrieved", user_id=current_user.id, count=len(care_requests))
    return care_requests

# ======= COMMENTARY MANAGEMENT =======

@app.post("/comments/", tags=["Comments"])
@trace_function("comment_creation")
async def create_comment(
        plant_id: int,
        comment: str,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """Create a comment on a plant."""
    logger.info("Creating comment", plant_id=plant_id, user_id=current_user.id)

    # Check if plant exists
    plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    if not plant:
        logger.error("Plant not found for comment", plant_id=plant_id)
        raise HTTPException(status_code=404, detail="Plant not found")

    # Create comment
    db_comment = models.Comment(
        plant_id=plant_id,
        user_id=current_user.id,
        comment=comment,
        time_stamp=dt.now()
    )

    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    # Enregistrer la métrique
    observability.record_comment_creation()

    logger.info("Comment created successfully",
                comment_id=db_comment.id,
                plant_id=plant_id,
                user_id=current_user.id)

    return db_comment

@app.get("/plants/{plant_id}/comments/", tags=["Comments"])
@trace_function("get_plant_comments")
async def get_plant_comments(
        plant_id: int,
        db: Session = Depends(get_db)
):
    """Get all comments for a specific plant."""
    logger.info("Getting plant comments", plant_id=plant_id)

    plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    if not plant:
        logger.error("Plant not found for comments", plant_id=plant_id)
        raise HTTPException(status_code=404, detail="Plant not found")

    comments = db.query(models.Comment).filter(models.Comment.plant_id == plant_id).all()

    logger.info("Plant comments retrieved", plant_id=plant_id, count=len(comments))
    return comments

@app.put("/comments/{comment_id}", tags=["Comments"])
@trace_function("comment_update")
async def update_comment(
        comment_id: int,
        comment_text: str,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """Update a comment."""
    logger.info("Updating comment", comment_id=comment_id, user_id=current_user.id)

    db_comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not db_comment:
        logger.error("Comment not found", comment_id=comment_id)
        raise HTTPException(status_code=404, detail="Comment not found")

    if db_comment.user_id != current_user.id:
        logger.warning("Unauthorized comment update attempt",
                       comment_id=comment_id,
                       user_id=current_user.id)
        raise HTTPException(status_code=403, detail="Not authorized to update this comment")

    db_comment.comment = comment_text
    db.commit()
    db.refresh(db_comment)

    logger.info("Comment updated successfully", comment_id=comment_id)
    return db_comment

@app.delete("/comments/{comment_id}", tags=["Comments"])
@trace_function("comment_deletion")
async def delete_comment(
        comment_id: int,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """Delete a comment."""
    logger.info("Deleting comment", comment_id=comment_id, user_id=current_user.id)

    db_comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not db_comment:
        logger.error("Comment not found for deletion", comment_id=comment_id)
        raise HTTPException(status_code=404, detail="Comment not found")

    plant = db.query(models.Plant).filter(models.Plant.id == db_comment.plant_id).first()

    if db_comment.user_id != current_user.id and plant.owner_id != current_user.id:
        logger.warning("Unauthorized comment deletion attempt",
                       comment_id=comment_id,
                       user_id=current_user.id)
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this comment. Must be comment author or plant owner."
        )

    db.delete(db_comment)
    db.commit()

    logger.info("Comment deleted successfully", comment_id=comment_id)
    return db_comment

@app.get("/users/{user_id}/comments/", tags=["Comments"])
@trace_function("get_user_comments")
async def get_user_comments(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Get all comments made by a specific user."""
    logger.info("Getting user comments", target_user_id=user_id, current_user_id=current_user.id)

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        logger.error("User not found for comments", user_id=user_id)
        raise HTTPException(status_code=404, detail="User not found")

    comments = db.query(models.Comment).filter(models.Comment.user_id == user_id).all()

    logger.info("User comments retrieved", user_id=user_id, count=len(comments))
    return comments