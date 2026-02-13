from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from .matter_client import read_temperature
from .database import engine, SessionLocal
from .models import Base, UserDB, DeviceDB, SensorDB
from .schemas import UserCreate, UserRead, DeviceCreate, DeviceRead, SensorCreate, SensorRead, WifiIn, CommissionIn

from .matter_ws import set_wifi_credentials, commission_with_code, read_temperature_c, get_nodes

app = FastAPI()
Base.metadata.create_all(bind=engine)
# router = APIRouter()

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

@app.post("/api/matter/wifi")
def api_set_wifi(payload: WifiIn):
    return set_wifi_credentials(payload.ssid, payload.password)

@app.post("/api/matter/commission")
def api_commission(payload: CommissionIn):
    # For Wi-Fi devices: call /api/matter/wifi first.
    return commission_with_code(payload.code, payload.node_id)

@app.get("/api/matter/nodes")
def api_nodes():
    return get_nodes()

@app.get("/api/matter/temperature/{node_id}")
def api_temp(node_id: int):
    temp = read_temperature_c(node_id)
    if temp is None:
        raise HTTPException(status_code=404, detail="Temperature not found on node (or node not reachable).")
    return {"node_id": node_id, "temperature_c": temp}

# @app.get("/api/matter/sensors/{node_id}")
# def api_sensors(node_id: int):
#     temp = read_temperature_c(node_id)
#     hum = read_humidity_rh(node_id)

#     if temp is None and hum is None:
#         raise HTTPException(status_code=404, detail="No sensor values found (node not reachable or not interviewed).")

#     return {"node_id": node_id, "temperature_c": temp, "humidity_rh": hum}

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

