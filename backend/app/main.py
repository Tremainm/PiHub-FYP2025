import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import engine, SessionLocal
from .models import Base, DeviceDB, SensorReadingDB
from .schemas import (
    DeviceCreate, DeviceRead,
    SensorReadingRead,
    WifiIn, CommissionIn,
    BrightnessIn, ColourXYIn,
)
from .matter_ws import (
    start_background_listener,
    register_callback,
    get_cached_temperature,
    get_cached_humidity,
    get_cached_sensor_data,
    get_cached_light_state,
    CONTEXT_LABELS,
    get_nodes,
    remove_node,
    set_wifi_credentials,
    commission_with_code,
    turn_on, turn_off, toggle,
    set_brightness,
    set_color_xy,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SENSOR_NODE_IDS = [1]

# -- DB helpers ----------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _persist_sensor_reading(node_id: int, sensor_type: str, value: float) -> None:
    """
    Write one sensor reading to the DB using its own short-lived session.

    This is a plain synchronous function intentionally. SQLAlchemy's
    synchronous Session must not be used inside async code directly.
    We call it via run_in_executor() from the async callback below so it
    runs in a thread pool and never blocks the event loop.
    """
    db = SessionLocal()
    try:
        db.add(SensorReadingDB(
            node_id=node_id,
            sensor_type=sensor_type,
            value=value,
            timestamp=datetime.now(timezone.utc),
        ))
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Failed to persist sensor reading: %s", exc)
    finally:
        db.close()


# -- Subscription callbacks ----------------------------------------------------

def _register_sensor_callbacks(sensor_node_ids: list[int]) -> None:
    """
    Register async callbacks for temperature, humidity, and context label.

    How it works:
      1. The background listener receives an attribute_updated event.
      2. It updates _attribute_cache (so /live endpoints stay fresh).
      3. It fires any callbacks registered for that (node_id, attribute_path).
      4. My callback converts the raw Matter value to a human unit and
         calls _persist_sensor_reading() in a thread pool so the DB write
         never blocks the async event loop.

    The attribute paths "1/1026/0" and "2/1029/0" are the exact strings
    python-matter-server uses in attribute_updated events for my device.
    """
    async def on_temperature(node_id: int, path: str, raw_value) -> None:
        if isinstance(raw_value, (int, float)):
            value = float(raw_value) / 100.0  # Matter stores temp as hundredths of a degree
            await asyncio.get_event_loop().run_in_executor(
                None, _persist_sensor_reading, node_id, "temperature_c", value
            )
            logger.debug("Persisted temperature node=%s %.2f°C", node_id, value)

    async def on_humidity(node_id: int, path: str, raw_value) -> None:
        if isinstance(raw_value, (int, float)):
            value = float(raw_value) / 100.0  # Matter stores humidity as hundredths of a percent
            await asyncio.get_event_loop().run_in_executor(
                None, _persist_sensor_reading, node_id, "humidity_rh", value
            )
            logger.debug("Persisted humidity node=%s %.2f%%", node_id, value)
    
    async def on_context(node_id: int, path: str, raw_value) -> None:
        """
        Persist context classification readings to the DB.
        Receives updates via MinMeasuredValue on the humidity cluster (workaround).
        Stored as sensor_type='context' with value 0/1/2.
        """
        if isinstance(raw_value, (int, float)):
            class_id = int(raw_value)
            label = CONTEXT_LABELS.get(class_id, "UNKNOWN")
            await asyncio.get_event_loop().run_in_executor(
                None, _persist_sensor_reading, node_id, "context", float(class_id)
            )
            logger.debug(
                "Persisted context node=%s class=%d label=%s", node_id, class_id, label
            )

    for node_id in sensor_node_ids:
        register_callback(node_id, "1/1026/0", on_temperature)
        register_callback(node_id, "2/1029/0", on_humidity)
        register_callback(node_id, "2/1029/1", on_context)   # MinMeasuredValue workaround
        logger.info("Registered sensor DB callbacks for node %s", node_id)


# -- Lifespan ------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_background_listener()
    # Brief pause to let the listener connect and complete the start_listening
    # handshake before we register callbacks. Without this the callbacks could
    # be registered before _attribute_cache is populated from the initial dump,
    # which is harmless but means the first few events might be missed.
    await asyncio.sleep(2)
    _register_sensor_callbacks(SENSOR_NODE_IDS)
    yield


# -- App setup -----------------------------------------------------------------

app = FastAPI(title="PiHub Matter API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -- Health --------------------------------------------------------------------

@app.get("/health", tags=["Health"])
def get_health():
    return {"status": "OK"}


# -- Device registry -----------------------------------------------------------

@app.get("/api/devices", response_model=list[DeviceRead], tags=["Devices"])
def list_devices(db: Session = Depends(get_db)):
    """List all registered devices (node_id + human-readable name)."""
    return list(db.execute(select(DeviceDB).order_by(DeviceDB.node_id)).scalars())


@app.post("/api/devices", response_model=DeviceRead, status_code=201, tags=["Devices"])
def register_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    """
    Register a friendly name for a commissioned Matter node.
    Call this after a successful commission so the UI shows names
    instead of raw node IDs.
    """
    device = DeviceDB(node_id=payload.node_id, name=payload.name)
    db.add(device)
    try:
        db.commit()
        db.refresh(device)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Node {payload.node_id} is already registered.")
    return device


@app.delete("/api/devices/{node_id}", status_code=204, tags=["Devices"])
def unregister_device(node_id: int, db: Session = Depends(get_db)):
    """
    Remove a device from the name registry.
    Does not decommission it from the Matter fabric.
    Call DELETE /api/matter/nodes/{node_id} for that.
    """
    device = db.execute(
        select(DeviceDB).where(DeviceDB.node_id == node_id)
    ).scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")
    db.delete(device)
    db.commit()


# -- Sensor history ------------------------------------------------------------

@app.get("/api/sensors/{node_id}/history", response_model=list[SensorReadingRead], tags=["Sensors"])
def get_sensor_history(node_id: int, sensor_type: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    """
    Return historical sensor readings for a node, newest first.
    Filter by sensor_type to get only temperature or only humidity.
    Default limit is 100 rows. Increase for charting longer time ranges.
    """
    stmt = (select(SensorReadingDB)
            .where(SensorReadingDB.node_id == node_id)
            .order_by(desc(SensorReadingDB.timestamp))
            .limit(limit)
    )
    if sensor_type:
        stmt = stmt.where(SensorReadingDB.sensor_type == sensor_type)
    return list(db.execute(stmt).scalars())


# -- Live sensor cache ---------------------------------------------------------

@app.get("/api/matter/nodes/{node_id}/sensors/live", tags=["Sensors"])
def api_cached_sensors(node_id: int):
    """
    Current temperature and humidity from the live subscription cache.
    Also returns TinyML context label
    """
    data = get_cached_sensor_data(node_id)
    if data["temperature_c"] is None and data["humidity_rh"] is None:
        raise HTTPException(
            status_code=404,
            detail="No sensor data cached yet. Check node_id or wait for first update.",
        )
    return {"node_id": node_id, **data}


@app.get("/api/matter/nodes/{node_id}/temperature/live", tags=["Sensors"])
def api_cached_temperature(node_id: int):
    """Latest temperature (°C) from the subscription cache."""
    temp = get_cached_temperature(node_id)
    if temp is None:
        raise HTTPException(status_code=404, detail="No temperature reading cached yet.")
    return {"node_id": node_id, "temperature_c": temp}


@app.get("/api/matter/nodes/{node_id}/humidity/live", tags=["Sensors"])
def api_cached_humidity(node_id: int):
    """Latest relative humidity (%RH) from the subscription cache."""
    hum = get_cached_humidity(node_id)
    if hum is None:
        raise HTTPException(status_code=404, detail="No humidity reading cached yet.")
    return {"node_id": node_id, "humidity_rh": hum}


# -- Live light state ----------------------------------------------------------

@app.get("/api/matter/nodes/{node_id}/state/live", tags=["Light state"])
def api_cached_light_state(node_id: int):
    """
    Current light state from the subscription cache: on/off, brightness, colour.
    The cache is kept fresh by the background subscription stream, which receives
    attribute_updated events whenever the bulb's state changes. The frontend polls
    this endpoint every 4 seconds, so the subscription's role is cache maintenance
    rather than push updates. It ensures polls always return current values,
    including changes made externally (e.g. a physical switch or another client).
    """
    state = get_cached_light_state(node_id)
    if all(v is None for v in state.values()):
        raise HTTPException(
            status_code=404,
            detail="No light state cached yet — check node_id or wait for first update.",
        )
    return {"node_id": node_id, **state}


# -- Node management -----------------------------------------------------------

@app.get("/api/matter/nodes", tags=["Nodes"])
async def api_nodes():
    """List all nodes in the Matter fabric."""
    return await get_nodes()


@app.delete("/api/matter/nodes/{node_id}", tags=["Nodes"])
async def api_remove_node(node_id: int):
    """
    Decommission a node from the Matter fabric.
    The device needs a factory reset before it can be re-commissioned.
    Also call DELETE /api/devices/{node_id} to remove it from the name registry.
    """
    return await remove_node(node_id)


# -- Commissioning -------------------------------------------------------------

@app.post("/api/matter/wifi", tags=["Commissioning"])
async def api_set_wifi(payload: WifiIn):
    """Pre-load Wi-Fi credentials. Call before /api/matter/commission for Wi-Fi devices."""
    return await set_wifi_credentials(payload.ssid, payload.password)


@app.post("/api/matter/commission", tags=["Commissioning"])
async def api_commission(payload: CommissionIn):
    """
    Commission a new Matter device. For Wi-Fi devices call /api/matter/wifi first.
    After success, call POST /api/devices to give the new node a friendly name.
    """
    return await commission_with_code(
        payload.code,
        node_id=payload.node_id,
        network_only=payload.network_only,
    )


# -- LED control ---------------------------------------------------------------

@app.post("/api/matter/nodes/{node_id}/on", tags=["LED control"])
async def api_light_on(node_id: int):
    """Turn a light on (OnOff:On)."""
    return await turn_on(node_id)


@app.post("/api/matter/nodes/{node_id}/off", tags=["LED control"])
async def api_light_off(node_id: int):
    """Turn a light off (OnOff:Off)."""
    return await turn_off(node_id)


@app.post("/api/matter/nodes/{node_id}/toggle", tags=["LED control"])
async def api_light_toggle(node_id: int):
    """Toggle on/off state (OnOff:Toggle)."""
    return await toggle(node_id)


@app.post("/api/matter/nodes/{node_id}/brightness", tags=["LED control"])
async def api_brightness(node_id: int, payload: BrightnessIn):
    """
    Set brightness (LevelControl:MoveToLevel).
    level: 0-254. transition_time: tenths of a second (0 = immediate).
    Use turn_off() rather than level=0 for a clean off.
    """
    return await set_brightness(node_id, payload.level, payload.transition_time)


@app.post("/api/matter/nodes/{node_id}/color/xy", tags=["LED control"])
async def api_color_xy(node_id: int, payload: ColourXYIn):
    """
    Set colour by CIE XY (ColorControl:MoveToColor).
    x, y: floats 0.0-1.0. transition_time: tenths of a second.

    Presets - Red: x=0.700 y=0.299 | Green: x=0.172 y=0.747
              Blue: x=0.136 y=0.040 | Warm white: x=0.450 y=0.408
    """
    return await set_color_xy(node_id, payload.x, payload.y, payload.transition_time)