from typing import Annotated
from pydantic import BaseModel, EmailStr, Field, StringConstraints, ConfigDict

UserNameStr = Annotated[str, StringConstraints(min_length=2, max_length=50)]
DeviceNameStr = Annotated[str, StringConstraints(min_length=2, max_length=30)]

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

class DeviceRead(BaseModel):
    id: int
    name: str
    status: str
    model_config = ConfigDict(from_attributes=True)