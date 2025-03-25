from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
from app.encryption import EncryptedFieldsMixin, setup_encryption_listeners

Base = declarative_base()

setup_encryption_listeners(Base)

class User(EncryptedFieldsMixin, Base):
    __tablename__ = "users"

    __encrypted_fields__ = ['email', 'phone', 'username']

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
    comments = relationship("Comment", 
                        back_populates="user",
                        cascade="all, delete-orphan")


class Plant(Base):
    __tablename__ = "plants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    location = Column(String)
    care_instructions = Column(String)
    photo_url = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    in_care_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    plant_sitting = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User",
                        foreign_keys=[owner_id],
                        back_populates="owned_plants",
                        lazy="joined")
    sitter = relationship("User",
                         foreign_keys=[plant_sitting],
                         primaryjoin="Plant.plant_sitting == User.id")
    comments = relationship("Comment", 
                          back_populates="plant",
                          cascade="all, delete-orphan")
    
class Comment(Base):
    __tablename__ = "commentary" 

    id = Column(Integer, primary_key=True, index=True)
    plant_id = Column(Integer, ForeignKey("plants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment = Column(String, nullable=False)
    
    user = relationship("User", back_populates="comments")
    plant = relationship("Plant", back_populates="comments")