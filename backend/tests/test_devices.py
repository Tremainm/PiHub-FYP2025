import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, get_db
from app.models import Base, DeviceDB

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
    db.query(DeviceDB).delete()
    db.commit()
    db.close()

    yield TestClient(app)

    app.dependency_overrides.clear()


# -- List ----------------------------------------------------------------------

def test_list_devices_empty(client):
    r = client.get("/api/devices")
    assert r.status_code == 200
    assert r.json() == []


def test_list_devices_returns_all(client):
    client.post("/api/devices", json={"node_id": 1, "name": "Lamp"})
    client.post("/api/devices", json={"node_id": 2, "name": "Strip"})
    r = client.get("/api/devices")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_devices_ordered_by_node_id(client):
    client.post("/api/devices", json={"node_id": 3, "name": "C"})
    client.post("/api/devices", json={"node_id": 1, "name": "A"})
    client.post("/api/devices", json={"node_id": 2, "name": "B"})
    node_ids = [d["node_id"] for d in client.get("/api/devices").json()]
    assert node_ids == sorted(node_ids)


# -- Register ------------------------------------------------------------------

def test_register_device_returns_201(client):
    r = client.post("/api/devices", json={"node_id": 1, "name": "Living Room"})
    assert r.status_code == 201


def test_register_device_response_shape(client):
    r = client.post("/api/devices", json={"node_id": 1, "name": "Living Room"})
    data = r.json()
    assert data["node_id"] == 1
    assert data["name"] == "Living Room"
    assert "id" in data


def test_register_duplicate_node_id_returns_409(client):
    client.post("/api/devices", json={"node_id": 5, "name": "First"})
    r = client.post("/api/devices", json={"node_id": 5, "name": "Second"})
    assert r.status_code == 409
    assert "already registered" in r.json()["detail"]


def test_register_device_name_too_short_returns_422(client):
    r = client.post("/api/devices", json={"node_id": 1, "name": "A"})
    assert r.status_code == 422


def test_register_device_name_too_long_returns_422(client):
    r = client.post("/api/devices", json={"node_id": 1, "name": "A" * 51})
    assert r.status_code == 422


def test_register_device_missing_name_returns_422(client):
    r = client.post("/api/devices", json={"node_id": 1})
    assert r.status_code == 422


def test_register_device_missing_node_id_returns_422(client):
    r = client.post("/api/devices", json={"name": "Lamp"})
    assert r.status_code == 422


# -- Unregister ----------------------------------------------------------------

def test_unregister_device_returns_204(client):
    client.post("/api/devices", json={"node_id": 3, "name": "Bulb"})
    r = client.delete("/api/devices/3")
    assert r.status_code == 204


def test_unregister_device_removes_from_list(client):
    client.post("/api/devices", json={"node_id": 3, "name": "Bulb"})
    client.delete("/api/devices/3")
    r = client.get("/api/devices")
    assert r.json() == []


def test_unregister_nonexistent_device_returns_404(client):
    r = client.delete("/api/devices/999")
    assert r.status_code == 404
    assert "Device not found" in r.json()["detail"]


def test_unregister_only_removes_target_device(client):
    client.post("/api/devices", json={"node_id": 1, "name": "Keep"})
    client.post("/api/devices", json={"node_id": 2, "name": "Remove"})
    client.delete("/api/devices/2")
    devices = client.get("/api/devices").json()
    assert len(devices) == 1
    assert devices[0]["node_id"] == 1
