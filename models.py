from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import func, String, Float, Datetime
from datetime import datetime

class Base(DeclarativeBase):
    pass

class UserDB(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

class Device(Base):
    __tablename__ = "devices"
    id = Mapped[int] = mapped_column(primary_key=True, index=True)
    name = Mapped[str] = mapped_column(String, nullable=False)
    status = Mapped[str] = mapped_column(String, nullable=False)

class SensorReading(Base):
    __tablename__ = "sensor_readings"
    id = Mapped[int] = mapped_column(primary_key=True, index=True)
    sensor_type = Mapped[str] = mapped_column(String, nullable=False)
    value = Mapped[float] = mapped_column(Float, nullable=False)
    timestamp = Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
