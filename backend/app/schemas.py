from typing import Annotated, Optional
from pydantic import BaseModel, StringConstraints, ConfigDict
from datetime import datetime

DeviceNameStr = Annotated[str, StringConstraints(min_length=2, max_length=50)]


# -- Device registry -----------------------------------------------------------

# BaseModel - validation, serialisation (JSON, HTTP), FastAPI integration (/docs)
class DeviceCreate(BaseModel):
    node_id: int
    name: DeviceNameStr

class DeviceRead(BaseModel):
    id: int
    node_id: int
    name: str

    # Read data from object attributes, not dict keys. i.e. device.node_id instead of device["node_id"]
    model_config = ConfigDict(from_attributes=True)     


# -- Sensor readings -----------------------------------------------------------

class SensorReadingRead(BaseModel):
    id: int
    node_id: int
    sensor_type: str   # "temperature_c" | "humidity_rh"
    value: float
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


# -- Matter command payloads ---------------------------------------------------

class WifiIn(BaseModel):
    ssid: str
    password: str

class CommissionIn(BaseModel):
    code: str
    node_id: Optional[int] = None
    network_only: bool = False

class BrightnessIn(BaseModel):
    level: int            # 0-254
    transition_time: int = 0  # tenths of a second

class ColourXYIn(BaseModel):
    x: float              # CIE x, 0.0-1.0
    y: float              # CIE y, 0.0-1.0
    transition_time: int = 0