import os
import fastapi.responses
from datetime import datetime as dt
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List
from app import schemas, auth, models
from app.security import security_manager
from app.database import engine, get_db
from app.config import settings

base_url = "localhost:8000"
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="A_rosa_je API")
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
async def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authentifie un utilisateur et renvoie un jeton JWT.

    Parameters:
    - form_data: Formulaire de demande OAuth2 contenant :
        - username: Email de l'utilisateur
        - password: Mot de passe de l'utilisateur

    Returns:
    - access_token: Jeton JWT pour l'authentification
    - token_type: Type de jeton (bearer)

    Raises:
    - 401: Si l'email ou le mot de passe est incorrect
    """
    # Recherchons l'utilisateur par son email en utilisant le hash
    email_hash = security_manager.hash_value(form_data.username)
    user = db.query(models.User).filter(models.User.email_hash == email_hash).first()
    
    # Vérifions si l'utilisateur existe et si le mot de passe est correct
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
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
    
    return {"access_token": access_token, "token_type": "bearer"}

# ======= USER MANAGEMENT =======

@app.post("/users/", response_model=schemas.User, tags=["Users"])
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Créer un nouvel utilisateur avec hashage et chiffrement des données sensibles"""
    
    # Vérifier l'unicité de l'email en utilisant le hash
    email_hash = security_manager.hash_value(user.email)
    db_user = db.query(models.User).filter(models.User.email_hash == email_hash).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Vérifier l'unicité du nom d'utilisateur en utilisant le hash
    username_hash = security_manager.hash_value(user.username)
    db_user = db.query(models.User).filter(models.User.username_hash == username_hash).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Créer l'utilisateur avec versions hashées et chiffrées
    db_user = models.User(
        # Versions hashées pour recherche et unicité
        email_hash=email_hash,
        username_hash=username_hash,
        phone_hash=security_manager.hash_value(user.phone),
        
        # Versions chiffrées pour stockage
        email_encrypted=security_manager.encrypt_value(user.email),
        username_encrypted=security_manager.encrypt_value(user.username),
        phone_encrypted=security_manager.encrypt_value(user.phone),
        
        # Autres champs
        hashed_password=auth.get_password_hash(user.password),
        is_botanist=user.is_botanist,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
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
async def edit_user(
    user_id: int,  
    email: EmailStr = None,
    username: str = None,
    phone: str = None,
    is_botanist: bool = None, 
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Met à jour un compte utilisateur existant.

    Parameters:
    - user_id: ID de l'utilisateur à mettre à jour
    - email: Nouvelle adresse email de l'utilisateur (optionnel)
    - username: Nouveau nom d'utilisateur (optionnel)
    - phone: Nouveau numéro de téléphone (optionnel)
    - is_botanist: Booléen indiquant si l'utilisateur est un botaniste (optionnel)

    Returns:
    - Objet utilisateur mis à jour

    Raises:
    - 404: Si l'utilisateur n'est pas trouvé
    - 400: Si l'email est déjà enregistré par un autre utilisateur
    - 403: Si on tente de mettre à jour un autre utilisateur sans les permissions adéquates
    """
    # Vérifier si l'utilisateur essaie de mettre à jour le profil de quelqu'un d'autre
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update other users")
        
    # Récupérer l'utilisateur à mettre à jour
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Vérifier si le nouvel email est déjà pris par quelqu'un d'autre
    if email and email != current_user.email:
        email_hash = security_manager.hash_value(email)
        existing_user = db.query(models.User).filter(models.User.email_hash == email_hash).first()
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Vérifier si le nouveau nom d'utilisateur est déjà pris
    if username and username != current_user.username:
        username_hash = security_manager.hash_value(username)
        existing_user = db.query(models.User).filter(models.User.username_hash == username_hash).first()
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Username already taken")
    
    # Mettre à jour les champs de l'utilisateur
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
    
    # Enregistrer les modifications
    db.commit()
    db.refresh(db_user)
    
    # Retourner les données déchiffrées
    return {
        "id": db_user.id,
        "email": security_manager.decrypt_value(db_user.email_encrypted),
        "username": security_manager.decrypt_value(db_user.username_encrypted),
        "phone": security_manager.decrypt_value(db_user.phone_encrypted),
        "is_active": db_user.is_active,
        "is_botanist": db_user.is_botanist
    }

@app.get("/users/me/", tags=["Users"])
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """
    Get details of the currently authenticated user.

    Returns:
    - User object with current user's details

    Requires:
    - Valid JWT token in Authorization header
    """
    return current_user

@app.delete("/users/", tags=["Users"])
async def delete_user(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """
        Delete a user account.

        Parameters:
        - id: ID of the user to delete

        Returns:
        - Deleted user object

        Raises:
        - 404: If user is not found

        Requires:
        - Valid JWT token in Authorization header
    """
    db_user = db.query(models.User).filter(models.User.id == id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return db_user


# ======= PLANT MANAGEMENT =======

@app.post("/plants/", tags=["Plants"])
async def create_plant(
        name: str,
        location: str,
        care_instructions: str | None = None,
        photo: UploadFile = File(),
        current_user: models.User = Depends(auth.get_current_user),
        in_care_id: int = None,
        db: Session = Depends(get_db)
):
    """
       Create a new plant entry.

       Parameters:
       - name: Name of the plant
       - location: Location of the plant
       - care_instructions: Optional care instructions
       - photo: Optional photo file of the plant

       Returns:
       - Created plant object

       Requires:
       - Valid JWT token in Authorization header
   """
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

    db.add(db_plant)
    db.commit()
    db.refresh(db_plant)
    return db_plant

@app.put("/plants/{plant_id}", tags=["Plants"])
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
    """
    Update an existing plant.

    Parameters:
    - plant_id: ID of the plant to update
    - name: New name of the plant (optional)
    - location: New location of the plant (optional)
    - care_instructions: New care instructions (optional)
    - photo: New photo file of the plant (optional)
    - in_care: New care status (optional)

    Returns:
    - Updated plant object

    Raises:
    - 404: If plant is not found or not owned by user

    Requires:
    - Valid JWT token in Authorization header
    """
    plant = db.query(models.Plant).filter(
        models.Plant.id == plant_id,
        models.Plant.owner_id == current_user.id
    ).first()
    
    if plant is None:
        raise HTTPException(
            status_code=404,
            detail="Plant not found or not owned by current user"
        )
    
    if name is not None:
        plant.name = name
    
    if location is not None:
        plant.location = location
    
    if care_instructions is not None:
        plant.care_instructions = care_instructions
    
    if in_care_id is not None:
        plant.in_care_id = in_care_id
    
    if photo and photo.filename:
        if plant.photo_url and os.path.exists(plant.photo_url.replace(f"{base_url}/", "")):
            try:
                os.remove(plant.photo_url.replace(f"{base_url}/", ""))
            except Exception as e:
                print(f"Error removing old photo: {e}")
        
        photo_filename = f"{current_user.id}_{photo.filename}"
        photo_path = f"photos/{photo_filename}"
        
        with open(photo_path, "wb") as buffer:
            content = await photo.read()
            buffer.write(content)
        
        plant.photo_url = f"{base_url}/photos/{photo_filename}"
    
    db.commit()
    db.refresh(plant)
    
    return plant

@app.delete("/plants", tags=["Plants"])
async def delete_plant(
        plant_id: int,
        db: Session = Depends(get_db)
):
    """
       Delete a plant.

       Parameters:
       - id: int: the id of the plant to delete

       Returns:
       - Modified plant object

       Requires:
       - Valid JWT token in Authorization header
   """
    plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    try:
        db.delete(plant)
        db.commit()
        return plant
    except Exception as e:
        return fastapi.HTTPException(
            status_code=404,
            detail="The plant was not found"
        )

@app.get("/my_plants/", tags=["Plants"])
async def list_plants_users_plant(
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """
       List all plants owned by the current user.

       Returns:
       - List of plant objects owned by the authenticated user

       Requires:
       - Valid JWT token in Authorization header
   """
    plants = db.query(models.Plant).filter(models.Plant.owner_id == current_user.id).all()
    for plant in plants:
        photofile = plant.photo_url
        if plant.photo_url:
            plant.photo_url = base_url + "/" +  photofile
    return plants

@app.get("/all_plants/", tags=["Plants"])
async def list_all_plants_except_users(
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """
       List all plants owned by the current user.

       Returns:
       - List of plant objects owned by the authenticated user

       Requires:
       - Valid JWT token in Authorization header
   """
    plants = db.query(models.Plant).filter(models.Plant.owner != current_user).all()
    for plant in plants:
        photofile = plant.photo_url
        if plant.photo_url:
            plant.photo_url = base_url + "/" +  photofile
    return plants


# ======= PLANT CARE =======

@app.put("/plants/{plant_id}/start-care", tags=["Plant Care"])
async def start_plant_care(
        plant_id: int,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """
        Start plant care by assigning a botanist.

        Parameters:
        - plant_id: ID of the plant to be cared for
        - botanist_id: ID of the botanist who will care for the plant

        Returns:
        - Updated plant object

        Raises:
        - 404: If plant is not found or not owned by user
        - 404: If botanist is not found

        Requires:
        - Valid JWT token in Authorization header
    """
    plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    plant.in_care_id = current_user.id
    db.commit()
    db.refresh(plant)
    return plant


@app.put("/plants/{plant_id}/end-care", tags=["Plant Care"])
async def end_plant_care(
        plant_id: int,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    if not plant or plant.in_care_id != current_user.id:
        raise HTTPException(status_code=404, detail="Plant not found or not caring by user")

    plant.in_care_id = None
    plant.plant_sitting = None
    db.commit()
    db.refresh(plant)
    return plant


@app.get("/care-requests/", tags=["Plant Care"])
async def list_care_requests(
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    care_requests = db.query(models.Plant).filter(
        models.Plant.in_care == True
    ).filter(
        models.Plant.owner_id != current_user.id
    ).all()
    for plant in care_requests:
        photofile = plant.photo_url
        if plant.photo_url:
            plant.photo_url = base_url + "/" +  photofile
    return care_requests

# ======= COMMENTARY MANAGEMENT =======

@app.post("/comments/", tags=["Comments"])
async def create_comment(
    plant_id: int,
    comment: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a comment on a plant.

    Parameters:
    - plant_id: ID of the plant to comment on
    - comment: Text of the comment

    Returns:
    - Created comment object

    Raises:
    - 404: If plant is not found

    Requires:
    - Valid JWT token in Authorization header
    """
    # Check if plant exists
    plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    if not plant:
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
    return db_comment


@app.get("/plants/{plant_id}/comments/", tags=["Comments"])
async def get_plant_comments(
    plant_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all comments for a specific plant.

    Parameters:
    - plant_id: ID of the plant to get comments for

    Returns:
    - List of comment objects

    Raises:
    - 404: If plant is not found

    Requires:
    - Valid JWT token in Authorization header
    """
    plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    comments = db.query(models.Comment).filter(models.Comment.plant_id == plant_id).all()
    return comments


@app.put("/comments/{comment_id}", tags=["Comments"])
async def update_comment(
    comment_id: int,
    comment_text: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a comment.

    Parameters:
    - comment_id: ID of the comment to update
    - comment_text: New text for the comment

    Returns:
    - Updated comment object

    Raises:
    - 404: If comment is not found
    - 403: If user is not the author of the comment

    Requires:
    - Valid JWT token in Authorization header
    """
    db_comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if db_comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this comment")
    
    db_comment.comment = comment_text
    db.commit()
    db.refresh(db_comment)
    return db_comment


@app.delete("/comments/{comment_id}", tags=["Comments"])
async def delete_comment(
    comment_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a comment.

    Parameters:
    - comment_id: ID of the comment to delete

    Returns:
    - Deleted comment object

    Raises:
    - 404: If comment is not found
    - 403: If user is not the author of the comment or plant owner

    Requires:
    - Valid JWT token in Authorization header
    """
    db_comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    plant = db.query(models.Plant).filter(models.Plant.id == db_comment.plant_id).first()
    
    if db_comment.user_id != current_user.id and plant.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="Not authorized to delete this comment. Must be comment author or plant owner."
        )
    
    db.delete(db_comment)
    db.commit()
    return db_comment


@app.get("/users/{user_id}/comments/", tags=["Comments"])
async def get_user_comments(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Get all comments made by a specific user.

    Parameters:
    - user_id: ID of the user to get comments for

    Returns:
    - List of comment objects

    Raises:
    - 404: If user is not found

    Requires:
    - Valid JWT token in Authorization header
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    comments = db.query(models.Comment).filter(models.Comment.user_id == user_id).all()
    return comments