import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

import database
from database import (
    User,
    Device,
    Reading,
    create_db_and_tables,
    get_db,
    get_password_hash,
    pwd_context,
    SessionLocal
)

# --- Configuration ---
SECRET_KEY = os.urandom(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- App Setup ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Security ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def seed_database(db: Session):
    # Check if data already exists
    if db.query(User).count() > 0:
        print("Database already seeded.")
        db.close()
        return

    # --- Create Users ---
    user1_pwd = get_password_hash('test')
    user1 = User(username='test', hashed_password=user1_pwd)

    user2_pwd = get_password_hash('test2')
    user2 = User(username='test2', hashed_password=user2_pwd)

    db.add_all([user1, user2])
    db.commit()

    # --- Create Devices ---
    device1 = Device(
        device_code="DEV001",
        name="London Weather Station",
        latitude=51.5074,
        longitude=-0.1278,
        owner=user1
    )

    device2 = Device(
        device_code="DEV002",
        name="New York Weather Station",
        latitude=40.7128,
        longitude=-74.0060,
        owner=user1
    )

    device3 = Device(
        device_code="DEV003",
        name="Tokyo Weather Station",
        latitude=35.6895,
        longitude=139.6917,
        owner=user2
    )
    
    db.add_all([device1, device2, device3])
    db.commit()

    # --- Create Readings ---
    # Readings for Device 1
    for i in range(10):
        reading = Reading(
            device=device1,
            temperature=20 + i * 0.5,
            pressure=1010 + i * 0.2,
            humidity=60 - i * 1.5,
            timestamp=datetime.utcnow() - timedelta(hours=i)
        )
        db.add(reading)

    # Readings for Device 2
    for i in range(5):
        reading = Reading(
            device=device2,
            temperature=25 - i * 0.8,
            pressure=1005 + i * 0.5,
            humidity=70 + i * 1.2,
            timestamp=datetime.utcnow() - timedelta(hours=i)
        )
        db.add(reading)

    db.commit()
    db.close()
    print("Database seeded successfully!")

@app.on_event("startup")
def on_startup():
    if os.path.exists("weather.db"):
        os.remove("weather.db")
    create_db_and_tables()
    db = SessionLocal()
    seed_database(db)


@app.on_event("shutdown")
def shutdown_event():
    database.engine.dispose()

# --- Pydantic Schemas ---
class TokenData(BaseModel):
    username: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str

class DeviceInfo(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    class Config:
        from_attributes = True

class ReadingCreate(BaseModel):
    device_code: str
    temperature: float
    pressure: float
    humidity: float

# --- Utility Functions ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(username=username)
    except JWTError:
        return None
    user = db.query(User).filter(User.username == token_data.username).first()
    return user

# --- Page Routes ---
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(response: Response, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        # Redirect back to login page with an error message
        return templates.TemplateResponse("login.html", {"request": {}, "error": "Invalid username or password"})

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
async def signup(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...)):
    db_user = db.query(User).filter(User.username == username).first()
    if db_user:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Username already registered"})
    
    hashed_password = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response

@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    user_with_devices = db.query(User).options(joinedload(User.devices)).filter(User.id == user.id).first()
    
    return templates.TemplateResponse("account.html", {"request": request, "user": user_with_devices})

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

    existing_device = db.query(Device).filter(Device.device_code == device_code).first()
    if existing_device:
        user_with_devices = db.query(User).options(joinedload(User.devices)).filter(User.id == user.id).first()
        return templates.TemplateResponse(
            "account.html",
            {
                "request": request,
                "user": user_with_devices,
                "error": "Device code already registered.",
            },
        )

    new_device = Device(
        device_code=device_code,
        name=device_name,
        latitude=latitude,
        longitude=longitude,
        user_id=user.id,
    )
    db.add(new_device)
    db.commit()

    return RedirectResponse(url="/account", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/readings", response_class=HTMLResponse)
async def readings_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # Eager load devices and their readings to prevent N+1 queries
    user_with_data = db.query(User).options(
        joinedload(User.devices).subqueryload(Device.readings)
    ).filter(User.id == user.id).first()

    return templates.TemplateResponse("readings.html", {"request": request, "user": user_with_data})


# --- API Endpoints ---
@app.get("/api/devices", response_model=List[DeviceInfo])
def get_devices(db: Session = Depends(get_db)):
    devices = db.query(Device).filter(Device.latitude.isnot(None), Device.longitude.isnot(None)).all()
    return devices