from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import func, String, ForeignKey, Float, DateTime
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class UserDB(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    devices: Mapped[list["DeviceDB"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

# One-to-many relationship (One User can have Many devices)
class DeviceDB(Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="OFF")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    owner: Mapped["UserDB"] = relationship(back_populates="devices")

class SensorDB(Base):
    __tablename__ = "sensors"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sensor_type: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
