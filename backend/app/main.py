from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from .database import engine, SessionLocal
from .models import Base, UserDB, DeviceDB, SensorDB
from .schemas import UserCreate, UserRead, DeviceCreate, DeviceRead, SensorCreate, SensorRead, WifiIn, CommissionIn

from .matter_ws import (set_wifi_credentials, commission_with_code,
                        read_temperature_c, read_humidity_rh, get_nodes, 
                        turn_on, turn_off, toggle, set_brightness, set_color_xy,
                        start_background_listener, get_cached_temperature, 
                        get_cached_humidity, get_cached_sensor_data
                        )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code here runs once on startup before any requests are handled.
    start_background_listener() launches a persistent asyncio task that
    keeps a websocket open to matter-server and caches attribute updates.
    """
    start_background_listener()
    yield
    # anything after yield runs on shutdown — nothing needed here

app = FastAPI(lifespan=lifespan)
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

#..... Set Wi-Fi credentials and commission (only if device has not previously been commissioned) .....

@app.post("/api/matter/wifi")
async def api_set_wifi(payload: WifiIn):
    return await set_wifi_credentials(payload.ssid, payload.password)

@app.post("/api/matter/commission")
async def api_commission(payload: CommissionIn):
    # For Wi-Fi devices: call /api/matter/wifi first.
    return await commission_with_code(payload.code, payload.node_id)

# ..... Get nodes of devices that are in the fabric .....

@app.get("/api/matter/nodes")
async def api_nodes():
    return await get_nodes()

# ..... One-shot call to get temperature, humidity, and both together .....

@app.get("/api/matter/temperature/{node_id}")
async def api_temp(node_id: int):
    temp = await read_temperature_c(node_id)
    if temp is None:
        raise HTTPException(status_code=404, detail="Temperature not found on node (or node not reachable).")
    return {"node_id": node_id, "temperature_c": temp}

@app.get("/api/matter/humidity/{node_id}")
async def api_humidity(node_id: int):
    hum = await read_humidity_rh(node_id)
    if hum is None:
        raise HTTPException(status_code=404, detail="Humidity not found.")
    return {"node_id": node_id, "humidity_rh": hum}

@app.get("/api/matter/sensors/{node_id}")
async def api_sensors(node_id: int):
    temp = await read_temperature_c(node_id)
    hum = await read_humidity_rh(node_id)

    if temp is None and hum is None:
        raise HTTPException(status_code=404, detail="No sensor values found (node not reachable or not interviewed).")

    return {"node_id": node_id, "temperature_c": temp, "humidity_rh": hum}

# ..... Subscription methods .....

@app.get("/api/matter/nodes/{node_id}/temperature/live")
async def api_cached_temperature(node_id: int):
    """
    Returns the latest temperature received via subscription (no network call).
    Much faster than /api/matter/temperature/{node_id} which does a fresh read.
    Returns 404 if no value has been received yet — call /subscribe first.
    """
    temp = get_cached_temperature(node_id)
    if temp is None:
        raise HTTPException(
            status_code=404,
            detail="No temperature reading cached yet. Call /subscribe on this node first."
        )
    return {"node_id": node_id, "temperature_c": temp}


@app.get("/api/matter/nodes/{node_id}/humidity/live")
async def api_cached_humidity(node_id: int):
    """
    Returns the latest humidity received via subscription (no network call).
    Returns 404 if no value has been received yet.
    """
    hum = get_cached_humidity(node_id)
    if hum is None:
        raise HTTPException(
            status_code=404,
            detail="No humidity reading cached yet. Call /subscribe on this node first."
        )
    return {"node_id": node_id, "humidity_rh": hum}


@app.get("/api/matter/nodes/{node_id}/sensors/live")
async def api_cached_sensors(node_id: int):
    """
    Returns both temperature and humidity from cache in one call.
    Either value may be None if not yet received.
    """
    data = get_cached_sensor_data(node_id)
    if data["temperature_c"] is None and data["humidity_rh"] is None:
        raise HTTPException(
            status_code=404,
            detail="No sensor data cached yet. Call /subscribe on this node first."
        )
    return {"node_id": node_id, **data}

# ..... LED control methods

@app.post("/api/matter/nodes/{node_id}/on")
async def api_light_on(node_id: int):
    """
    Sends the OnOff:On command to endpoint 1 of the given node.
    The light example uses endpoint 1 for its OnOff cluster.
    """
    return await turn_on(node_id)


@app.post("/api/matter/nodes/{node_id}/off")
async def api_light_off(node_id: int):
    """
    Sends the OnOff:Off command to endpoint 1 of the given node.
    """
    return await turn_off(node_id)


@app.post("/api/matter/nodes/{node_id}/toggle")
async def api_light_toggle(node_id: int):
    """
    Sends the OnOff:Toggle command — flips current state without needing to know it.
    Useful for a single button press.
    """
    return await toggle(node_id)

@app.post("/api/matter/nodes/{node_id}/brightness/{level}")
async def api_brightness(node_id: int, level: int):
    """
    Set brightness. level is 0-254.
    Example: POST /api/matter/nodes/3/brightness/128  sets to 50% brightness.
    """
    return await set_brightness(node_id, level)

@app.post("/api/matter/nodes/{node_id}/color/xy")
async def api_color_xy(node_id: int, x: float, y: float):
    """
    Set colour by CIE XY coordinates (both 0.0-1.0).
    Example: POST /api/matter/nodes/3/color/xy?x=0.700&y=0.299  sets red.
    """
    return await set_color_xy(node_id, x, y)

# @app.get("/api/users", response_model=list[UserRead])
# def list_users(db: Session = Depends(get_db)):
#     stmt = select(UserDB).order_by(UserDB.id)
#     return list(db.execute(stmt).scalars())

# @app.get("/api/users/{user_id}", response_model=UserRead)
# def get_user(user_id: int, db: Session = Depends(get_db)):
#     user = db.get(UserDB, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user

# @app.post("/api/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
# def add_user(payload: UserCreate, db: Session = Depends(get_db)):
#     user = UserDB(**payload.model_dump())
#     db.add(user)
#     try:
#         db.commit()
#         db.refresh(user)
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=409, detail="User already exists")
#     return user

# @app.get("/api/devices", response_model=list[DeviceRead])
# def list_devices(db: Session = Depends(get_db)):
#     stmt = select(DeviceDB).order_by(DeviceDB.id)
#     return list(db.execute(stmt).scalars())

# @app.get("/api/devices/{device_id}", response_model=DeviceRead)
# def get_device(device_id: int, db: Session = Depends(get_db)):
#     device = db.get(DeviceDB, device_id)
#     if not device:
#         raise HTTPException(status_code=404, detail="Device not found")
#     return device

# @app.post("/api/devices", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
# def add_device(payload: DeviceCreate, db: Session = Depends(get_db)):
#     device = DeviceDB(**payload.model_dump())
#     db.add(device)
#     try:
#         db.commit()
#         db.refresh(device)
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=409, detail="Device already exists")
#     return device

# @app.put("/api/devices/{device_id}/toggle", response_model=DeviceRead)
# def toggle_device(device_id: int, db: Session = Depends(get_db)):
#     device = db.get(DeviceDB, device_id)
#     if not device:
#         raise HTTPException(status_code=404, detail="Device not found")

#     device.status = "OFF" if device.status.upper() == "ON" else "ON"

#     db.add(device)
#     try:
#         db.commit()
#         db.refresh(device)
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=409, detail="Device status not updated")

#     return device

