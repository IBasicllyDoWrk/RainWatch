
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from passlib.context import CryptContext

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

# Database setup
DATABASE_URL = "sqlite:///./weather.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    devices = relationship("Device", back_populates="owner")

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    device_code = Column(String, unique=True, index=True)
    name = Column(String, index=True, default="My Weather Station")
    latitude = Column(Float)
    longitude = Column(Float)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="devices")
    readings = relationship("Reading", back_populates="device")

class Reading(Base):
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    temperature = Column(Float)
    pressure = Column(Float)
    humidity = Column(Float)
    device_id = Column(Integer, ForeignKey("devices.id"))
    device = relationship("Device", back_populates="readings")

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
