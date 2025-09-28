import os
from datetime import datetime, timedelta, UTC
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

# Local imports
import database
from database import (
    User,
    Device,
    Reading,
    create_db_and_tables,
    get_db,
    get_password_hash,
    verify_password,
)

# --- Configuration ---
SECRET_KEY = os.urandom(32).hex()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# --- Pydantic Schemas ---
class SensorData(BaseModel):
    temperature_c: float
    humidity: float
    pressure: Optional[float] = None


class DeviceInfo(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float

    class Config:
        from_attributes = True


class LatestReading(BaseModel):
    device_id: int
    device_name: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    timestamp: Optional[datetime] = None
    rain_chance: int = 0  # Placeholder for rain prediction

    class Config:
        from_attributes = True


# --- Lifespan for application startup/shutdown ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    print("Application startup: Ensuring database tables exist...")
    create_db_and_tables()
    print("Database is ready.")
    yield
    print("Application shutdown initiated.")
    database.engine.dispose()


# --- App Setup ---
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# --- Utility Functions ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    """Decodes JWT from cookie and retrieves the user from the database."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    return db.query(User).filter(User.username == username).first()


# --- Page Routes (HTML) ---
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: Optional[User] = Depends(get_current_user)):
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response


@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@app.post("/signup")
async def signup(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "Username already registered"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    new_user = User(username=username, hashed_password=get_password_hash(password))
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response


@app.get("/account", response_class=HTMLResponse)
async def account_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    user_with_devices = (
        db.query(User)
        .options(joinedload(User.devices))
        .filter(User.id == user.id)
        .first()
    )
    return templates.TemplateResponse(
        "account.html", {"request": request, "user": user_with_devices}
    )


@app.post("/account/register-device")
async def register_device(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    device_code: str = Form(...),
    device_name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if db.query(Device).filter(Device.device_code.ilike(device_code)).first():
        user_with_devices = (
            db.query(User)
            .options(joinedload(User.devices))
            .filter(User.id == user.id)
            .first()
        )
        return templates.TemplateResponse(
            "account.html",
            {
                "request": request,
                "user": user_with_devices,
                "error": "Device code already registered.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    new_device = Device(
        device_code=device_code.upper(),
        name=device_name,
        latitude=latitude,
        longitude=longitude,
        user_id=user.id,
    )
    db.add(new_device)
    db.commit()
    return RedirectResponse(url="/account", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/readings", response_class=HTMLResponse)
async def readings_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    user_with_data = (
        db.query(User)
        .options(joinedload(User.devices).subqueryload(Device.readings))
        .filter(User.id == user.id)
        .first()
    )
    return templates.TemplateResponse(
        "readings.html", {"request": request, "user": user_with_data}
    )


# --- API Endpoints (JSON) ---
@app.post("/api/sensor-data", status_code=status.HTTP_201_CREATED, tags=["API"])
@app.post(
    "/api/sensor-data/",
    status_code=status.HTTP_201_CREATED,
    tags=["API"],
    include_in_schema=False,
)
async def receive_sensor_data(
    request: Request, sensor_data: SensorData, db: Session = Depends(get_db)
):
    device_code = request.headers.get("deviceCode")
    if not device_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="deviceCode header is required",
        )

    cleaned_code = device_code.strip()
    device = db.query(Device).filter(Device.device_code.ilike(cleaned_code)).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with code '{cleaned_code}' not found",
        )

    new_reading = Reading(
        temperature=sensor_data.temperature_c,
        humidity=sensor_data.humidity,
        pressure=sensor_data.pressure,
        device_id=device.id,
    )
    db.add(new_reading)
    db.commit()
    return {"message": "Data recorded successfully"}


@app.get("/api/devices", response_model=List[DeviceInfo], tags=["API"])
def get_devices(db: Session = Depends(get_db)):
    """Returns a list of all devices with valid coordinates."""
    return (
        db.query(Device)
        .filter(Device.latitude.isnot(None), Device.longitude.isnot(None))
        .all()
    )


@app.get("/api/devices/{device_id}/latest", response_model=LatestReading, tags=["API"])
def get_latest_reading(device_id: int, db: Session = Depends(get_db)):
    """Returns the latest reading for a specific device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with id {device_id} not found"
        )
    
    # Get the most recent reading for this device
    latest_reading = (
        db.query(Reading)
        .filter(Reading.device_id == device_id)
        .order_by(Reading.timestamp.desc())
        .first()
    )
    
    # Calculate a simple rain chance based on humidity (this is a placeholder)
    rain_chance = 0
    if latest_reading and latest_reading.humidity:
        if latest_reading.humidity > 80:
            rain_chance = 75
        elif latest_reading.humidity > 60:
            rain_chance = 45
        elif latest_reading.humidity > 40:
            rain_chance = 20
        else:
            rain_chance = 5
    
    return LatestReading(
        device_id=device.id,
        device_name=device.name,
        temperature=latest_reading.temperature if latest_reading else None,
        humidity=latest_reading.humidity if latest_reading else None,
        pressure=latest_reading.pressure if latest_reading else None,
        timestamp=latest_reading.timestamp if latest_reading else None,
        rain_chance=rain_chance
    )
