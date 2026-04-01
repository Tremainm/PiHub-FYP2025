import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, get_db
from app.models import Base, SensorReadingDB

TEST_DB_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(bind=engine)


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Wipe tables before each test
    db = TestingSessionLocal()
    db.query(SensorReadingDB).delete()
    db.commit()
    db.close()

    yield TestClient(app)

    app.dependency_overrides.clear()


def _seed(node_id: int, sensor_type: str, value: float):
    """Insert a reading directly into the test DB."""
    db = TestingSessionLocal()
    db.add(SensorReadingDB(
        node_id=node_id,
        sensor_type=sensor_type,
        value=value,
        timestamp=datetime.now(timezone.utc),
    ))
    db.commit()
    db.close()


# -- History endpoint ----------------------------------------------------------

def test_sensor_history_empty(client):
    r = client.get("/api/sensors/1/history")
    assert r.status_code == 200
    assert r.json() == []


def test_sensor_history_returns_readings(client):
    _seed(1, "temperature_c", 21.5)
    _seed(1, "temperature_c", 22.0)
    r = client.get("/api/sensors/1/history")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_sensor_history_filter_by_sensor_type(client):
    _seed(1, "temperature_c", 21.5)
    _seed(1, "humidity_rh", 55.0)
    r = client.get("/api/sensors/1/history?sensor_type=temperature_c")
    data = r.json()
    assert len(data) == 1
    assert data[0]["sensor_type"] == "temperature_c"


def test_sensor_history_filter_excludes_other_types(client):
    _seed(1, "temperature_c", 21.5)
    _seed(1, "humidity_rh", 55.0)
    _seed(1, "context", 1.0)
    r = client.get("/api/sensors/1/history?sensor_type=humidity_rh")
    data = r.json()
    assert all(row["sensor_type"] == "humidity_rh" for row in data)


def test_sensor_history_respects_limit(client):
    for i in range(10):
        _seed(1, "temperature_c", float(i))
    r = client.get("/api/sensors/1/history?limit=5")
    assert len(r.json()) == 5


def test_sensor_history_ordered_newest_first(client):
    _seed(1, "temperature_c", 20.0)
    _seed(1, "temperature_c", 25.0)
    data = client.get("/api/sensors/1/history").json()
    # Newer insert has higher value; newest should be first
    assert data[0]["value"] == 25.0


def test_sensor_history_isolates_node_ids(client):
    _seed(1, "temperature_c", 20.0)
    _seed(2, "temperature_c", 30.0)
    r1 = client.get("/api/sensors/1/history").json()
    r2 = client.get("/api/sensors/2/history").json()
    assert len(r1) == 1 and r1[0]["value"] == 20.0
    assert len(r2) == 1 and r2[0]["value"] == 30.0


def test_sensor_history_reading_has_expected_fields(client):
    _seed(1, "temperature_c", 21.5)
    reading = client.get("/api/sensors/1/history").json()[0]
    assert "id" in reading
    assert "node_id" in reading
    assert "sensor_type" in reading
    assert "value" in reading
    assert "timestamp" in reading


def test_sensor_history_context_readings(client):
    _seed(1, "context", 0.0)
    _seed(1, "context", 1.0)
    r = client.get("/api/sensors/1/history?sensor_type=context")
    assert len(r.json()) == 2


def test_sensor_history_no_filter_returns_all_types(client):
    _seed(1, "temperature_c", 21.5)
    _seed(1, "humidity_rh", 55.0)
    _seed(1, "context", 1.0)
    data = client.get("/api/sensors/1/history").json()
    types = {row["sensor_type"] for row in data}
    assert types == {"temperature_c", "humidity_rh", "context"}
