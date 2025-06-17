import pydantic
import datetime


class UserBase(pydantic.BaseModel):
    """The base model of a User"""
    email: pydantic.EmailStr
    username: str
    phone: str

class UserCreate(UserBase):
    """The model for a user creation"""
    username: str
    phone: str
    password: str
    is_botanist: bool = False

class UserDelete(UserBase):
    """The model to delete a user"""

    id: str

class User(UserBase):
    id: int
    is_active: bool
    is_botanist: bool

    class Config:
        from_attributes = True

class PlantBase(pydantic.BaseModel):
    name: str
    location: str
    care_instructions: str | None = None

class PlantCreate(PlantBase):
    pass

class Plant(PlantBase):
    id: int
    photo_url: str | None
    owner: User
    created_at: datetime.datetime
    in_care: bool
    plant_sitting: int | None

    class Config:
        from_attributes = True