from typing import Annotated
from pydantic import BaseModel, EmailStr, Field, StringConstraints, ConfigDict
from datetime import datetime

UserNameStr = Annotated[str, StringConstraints(min_length=2, max_length=50)]
DeviceNameStr = Annotated[str, StringConstraints(min_length=2, max_length=30)]
SensorTypeStr = Annotated[str, StringConstraints(min_length=2, max_length=20)]

class UserCreate(BaseModel):
    name: UserNameStr
    email: EmailStr

class UserRead(BaseModel):
    id: int
    name: UserNameStr
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)

class DeviceCreate(BaseModel):
    name: DeviceNameStr
    owner_id: int

class DeviceRead(BaseModel):
    id: int
    name: str
    status: str
    owner_id: int
    model_config = ConfigDict(from_attributes=True)

class SensorCreate(BaseModel):
    sensor_type: SensorTypeStr
    value: float

class SensorRead(BaseModel):
    id: int
    sensor_type: SensorTypeStr
    value: float
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)