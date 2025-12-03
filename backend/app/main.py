from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .database import engine, SessionLocal
from .models import Base, UserDB, DeviceDB, SensorDB
from .schemas import UserCreate, UserRead, DeviceCreate, DeviceRead, SensorCreate, SensorRead

app = FastAPI()
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def get_health():
    return { "status": "OK"}

@app.get("/api/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    stmt = select(UserDB).order_by(UserDB.id)
    return list(db.execute(stmt).scalars())

@app.get("/api/users/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(UserDB, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def add_user(payload: UserCreate, db: Session = Depends(get_db)):
    user = UserDB(**payload.model_dump())
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User already exists")
    return user

@app.get("/api/devices", response_model=list[DeviceRead])
def list_devices(db: Session = Depends(get_db)):
    stmt = select(DeviceDB).order_by(DeviceDB.id)
    return list(db.execute(stmt).scalars())

@app.get("/api/devices/{device_id}", response_model=DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = db.get(DeviceDB, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@app.post("/api/devices", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def add_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    device = DeviceDB(**payload.model_dump())
    db.add(device)
    try:
        db.commit()
        db.refresh(device)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Device already exists")
    return device

@app.put("/api/devices/{device_id}/toggle", response_model=DeviceRead)
def toggle_device(device_id: int, db: Session = Depends(get_db)):
    device = db.get(DeviceDB, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.status = "OFF" if device.status.upper() == "ON" else "ON"

    db.add(device)
    try:
        db.commit()
        db.refresh(device)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Device status not updated")

    return device

@app.get("/api/sensors", response_model=list[SensorRead])
def list_sensors(db: Session = Depends(get_db)):
    stmt = select(SensorDB).order_by(SensorDB.id)
    return list(db.execute(stmt).scalars())

@app.get("/api/sensors/{sensor_id}", response_model=SensorRead)
def get_sensor(sensor_id: int, db: Session = Depends(get_db)):
    sensor = db.get(SensorDB, sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor

@app.post("/api/sensors", response_model=SensorRead, status_code=status.HTTP_201_CREATED)
def add_sensor_reading(payload: SensorCreate, db: Session = Depends(get_db)):
    reading = SensorDB(**payload.model_dump())
    db.add(reading)
    try:
        db.commit()
        db.refresh(device)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Device status not updated")

    return reading

# JUST FOR TESTING
@app.post("/api/sensors/seed")
def seed_sensors(db: Session = Depends(get_db)):
    dummy = [
        SensorDB(sensor_type="temperature", value=22.1),
        SensorDB(sensor_type="temperature", value=23.4),
        SensorDB(sensor_type="humidity", value=44.6),
    ]
    db.add_all(dummy)
    db.commit()
    return {"added": len(dummy)}

