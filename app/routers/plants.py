import os
from datetime import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app import models, auth
from app.database import get_db
from app.observability import observability, trace_function, get_logger

router = APIRouter()
logger = get_logger()
base_url = "localhost:8000"

@router.post("/plants/", tags=["Plants"])
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
    logger.info(
        "Creating new plant",
        plant_name=name,
        location=location,
        owner_id=current_user.id
    )

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

    owner_type = "botanist" if current_user.is_botanist else "regular"
    observability.record_plant_creation(owner_type)

    logger.info(
        "Plant created successfully",
        plant_id=db_plant.id,
        owner_type=owner_type
    )

    return db_plant

@router.put("/plants/{plant_id}", tags=["Plants"])
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
        logger.error(
            "Plant not found or not owned by user",
            plant_id=plant_id,
            user_id=current_user.id
        )
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

@router.delete("/plants", tags=["Plants"])
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

@router.get("/my_plants/", tags=["Plants"])
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

@router.get("/all_plants/", tags=["Plants"])
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

@router.put("/plants/{plant_id}/start-care", tags=["Plant Care"])
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

    observability.record_care_request("start")

    logger.info("Plant care started", plant_id=plant_id, botanist_id=current_user.id)
    return plant

@router.put("/plants/{plant_id}/end-care", tags=["Plant Care"])
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
        logger.error(
            "Plant not found or not caring by user",
            plant_id=plant_id,
            user_id=current_user.id
        )
        raise HTTPException(status_code=404, detail="Plant not found or not caring by user")

    plant.in_care_id = None
    plant.plant_sitting = None
    db.commit()
    db.refresh(plant)

    observability.record_care_request("end")

    logger.info("Plant care ended", plant_id=plant_id, botanist_id=current_user.id)
    return plant

@router.get("/care-requests/", tags=["Plant Care"])
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
