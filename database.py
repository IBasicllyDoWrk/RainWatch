import os
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, UTC
import bcrypt


# --- Corrected Password Hashing and Verification ---
def get_password_hash(password: str) -> str:
    """Hashes a password using bcrypt."""
    # Ensure password is encoded as UTF-8 and truncated to 72 bytes as per bcrypt's limitation
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    try:
        # Convert the plain password and the stored hash back to bytes
        plain_password_bytes = plain_password.encode("utf-8")[:72]
        hashed_password_bytes = hashed_password.encode("utf-8")
        # Verify the password
        return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
    except (ValueError, TypeError):
        # Handle cases where the hashed_password is not a valid hash
        return False


# --- Database Setup ---
# Use environment variable for database path to support Docker volumes
DB_PATH = os.getenv("DB_PATH", "./weather.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- Database Models ---
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
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    temperature = Column(Float)
    pressure = Column(Float)
    humidity = Column(Float)
    device_id = Column(Integer, ForeignKey("devices.id"))
    device = relationship("Device", back_populates="readings")


def create_db_and_tables():
    """Creates all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
