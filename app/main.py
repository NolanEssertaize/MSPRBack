import os
import fastapi.responses
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List
from app import schemas, auth, models
from app.database import engine, get_db
from app.config import settings

base_url = "localhost:8000"
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="A_rosa_je API")
# Create the photos directory if it doesn't exist
os.makedirs("photos", exist_ok=True)

# Add this after creating the FastAPI app
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
        Authenticate a user and return a JWT token.

        Parameters:
        - form_data: OAuth2 password request form containing:
            - username: User's email
            - password: User's password

        Returns:
        - access_token: JWT token for authentication
        - token_type: Type of token (bearer)

        Raises:
        - 401: If email or password is incorrect
        """
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ======= USER MANAGEMENT =======

@app.post("/users/", response_model=schemas.User, tags=["Users"])
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
        Create a new user account.

        Parameters:
        - user: User creation schema containing:
            - email: User's email address
            - password: User's password
            - is_botanist: Boolean indicating if user is a botanist

        Returns:
        - User object with created user details

        Raises:
        - 400: If email is already registered
    """
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email, 
        phone=user.phone,
        hashed_password=hashed_password, 
        is_botanist=user.is_botanist)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.put("/users/{user_id}", tags=["Users"])
async def edit_user(
    user_id: int,  
    email: EmailStr = None,
    username: str = None,
    phone: str = None,
    is_botanist: bool = None, 
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing user account.

    Parameters:
    - user_id: ID of the user to update
    - email: User's new email address (optional)
    - username: User's new username (optional)
    - phone: User's new phone number (optional)
    - is_botanist: Boolean indicating if user is a botanist (optional)

    Returns:
    - Updated user object

    Raises:
    - 404: If user is not found
    - 400: If email is already registered by another user
    - 403: If trying to update another user without proper permissions
    """
    # Check if user is trying to update someone else's profile
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update other users")
        
    # Get the user to update
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if the new email is already taken by someone else
    if email and email != db_user.email:
        existing_user = db.query(models.User).filter(models.User.email == email).first()
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Update user fields
    if email is not None:
        db_user.email = email
    if username is not None:
        db_user.username = username
    if phone is not None:
        db_user.phone = phone
    if is_botanist is not None:
        db_user.is_botanist = is_botanist
    
    # Commit changes
    db.commit()
    db.refresh(db_user)
    return db_user

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
        in_care: bool = False,
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
        "in_care": in_care
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
        in_care: bool = None,
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
    
    if in_care is not None:
        plant.in_care = in_care
    
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
    plants = db.query(models.Plant).filter(models.Plant.owner == current_user).all()
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
    if not plant or plant.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Plant not found or not owned by user")

    plant.in_care = True
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
    if not plant or plant.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Plant not found or not owned by user")

    plant.in_care = False
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