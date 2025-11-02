from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, TIMESTAMP ,  LargeBinary
from sqlalchemy.orm import relationship 
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50))
    first_name = Column(String(100))
    last_name = Column(String(100))
    home_address = Column(String(255))
    email = Column(String(255), unique=True, index=True)
    field_of_study = Column(String(255))
    year = Column(Integer)
    password = Column(String(255))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    lost_items = relationship("LostItem", back_populates="user", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="user", cascade="all, delete-orphan")

class LostItem(Base):
    __tablename__ = "lost_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    item_name = Column(String(255), nullable=False)
    item_description = Column(Text, nullable=False)
    item_image = Column(LargeBinary, nullable=True)
    email = Column(String(255), nullable=False)
    date = Column(TIMESTAMP, nullable=False)
    location = Column(String(255), nullable=False)
    found = Column(Boolean, default=False)   # True if the item has been found
    status = Column(String(50), default="pending")  # pending / approved / rejected
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)  # Track edits

    user = relationship("User", back_populates="lost_items")
    claims = relationship("Claim", back_populates="item", cascade="all, delete-orphan")

class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    item_id = Column(Integer, ForeignKey("lost_items.id"))
    claim_message = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending / approved / rejected
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)  # Track claim edits

    user = relationship("User", back_populates="claims")
    item = relationship("LostItem", back_populates="claims")
