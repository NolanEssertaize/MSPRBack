from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    phone = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_botanist = Column(Boolean, default=False)
    owned_plants = relationship("Plant",
                                back_populates="owner",
                                foreign_keys="[Plant.owner_id]")


class Plant(Base):
    __tablename__ = "plants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    location = Column(String)
    care_instructions = Column(String)
    photo_url = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    in_care = Column(Boolean, default=False)
    plant_sitting = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Define both relationships here
    owner = relationship("User",
                         foreign_keys=[owner_id],
                         back_populates="owned_plants",
                         lazy="joined")
    sitter = relationship("User",
                          foreign_keys=[plant_sitting],
                          primaryjoin="Plant.plant_sitting == User.id")