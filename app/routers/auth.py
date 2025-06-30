from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import auth, models
from app.database import get_db
from app.security import security_manager
from app.config import settings
from app.observability import observability, trace_function, get_logger

router = APIRouter()
logger = get_logger()

@router.post("/token", tags=["Authentication"])
@trace_function("user_authentication")
async def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    
    logger.info("User login attempt", email=form_data.username)

    email_hash = security_manager.hash_value(form_data.username)
    user = db.query(models.User).filter(models.User.email_hash == email_hash).first()

    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        logger.warning("Failed login attempt", email=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": security_manager.decrypt_value(user.email_encrypted)},
        expires_delta=access_token_expires
    )

    logger.info("User login successful", user_id=user.id, is_botanist=user.is_botanist)
    observability.set_current_user(str(user.id))

    return {"access_token": access_token, "token_type": "bearer"}
