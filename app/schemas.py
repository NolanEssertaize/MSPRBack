from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    username: str
    phone: str

class UserCreate(UserBase):
    username: str
    phone: str
    password: str
    is_botanist: bool = False

class UserDelete(UserBase):
    id: str

class User(UserBase):
    id: int
    is_active: bool
    is_botanist: bool

    class Config:
        from_attributes = True

class PlantBase(BaseModel):
    name: str
    location: str
    care_instructions: str | None = None

class PlantCreate(PlantBase):
    pass

class Plant(PlantBase):
    id: int
    photo_url: str | None
    owner: User
    created_at: datetime
    in_care: bool
    plant_sitting: int | None

    class Config:
        from_attributes = True