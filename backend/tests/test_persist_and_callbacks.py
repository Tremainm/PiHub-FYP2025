"""
Tests for _persist_sensor_reading and the three sensor callbacks
(_register_sensor_callbacks inner functions).

Uses an in-memory SQLite DB and patches app.main.SessionLocal so
no real DB connection is required.
"""
import asyncio
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, SensorReadingDB
from app.main import _persist_sensor_reading, _register_sensor_callbacks
from app.matter_ws import _subscribers

TEST_DB_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def clean():
    db = TestingSessionLocal()
    db.query(SensorReadingDB).delete()
    db.commit()
    db.close()
    _subscribers.clear()
    yield
    _subscribers.clear()


# -- _persist_sensor_reading ---------------------------------------------------

class TestPersistSensorReading:
    def test_persists_temperature_reading(self):
        with patch("app.main.SessionLocal", TestingSessionLocal):
            _persist_sensor_reading(1, "temperature_c", 21.5)

        db = TestingSessionLocal()
        row = db.query(SensorReadingDB).first()
        db.close()

        assert row.node_id == 1
        assert row.sensor_type == "temperature_c"
        assert row.value == pytest.approx(21.5)

    def test_persists_humidity_reading(self):
        with patch("app.main.SessionLocal", TestingSessionLocal):
            _persist_sensor_reading(1, "humidity_rh", 59.4)

        db = TestingSessionLocal()
        row = db.query(SensorReadingDB).first()
        db.close()

        assert row.sensor_type == "humidity_rh"
        assert row.value == pytest.approx(59.4)

    def test_persists_context_reading(self):
        with patch("app.main.SessionLocal", TestingSessionLocal):
            _persist_sensor_reading(1, "context", 1.0)

        db = TestingSessionLocal()
        row = db.query(SensorReadingDB).first()
        db.close()

        assert row.sensor_type == "context"
        assert row.value == pytest.approx(1.0)

    def test_timestamp_is_stored(self):
        with patch("app.main.SessionLocal", TestingSessionLocal):
            _persist_sensor_reading(1, "temperature_c", 20.0)

        db = TestingSessionLocal()
        row = db.query(SensorReadingDB).first()
        db.close()

        assert row.timestamp is not None

    def test_multiple_readings_each_stored(self):
        with patch("app.main.SessionLocal", TestingSessionLocal):
            _persist_sensor_reading(1, "temperature_c", 20.0)
            _persist_sensor_reading(1, "temperature_c", 21.0)
            _persist_sensor_reading(1, "humidity_rh", 55.0)

        db = TestingSessionLocal()
        assert db.query(SensorReadingDB).count() == 3
        db.close()

    def test_different_node_ids_stored_separately(self):
        with patch("app.main.SessionLocal", TestingSessionLocal):
            _persist_sensor_reading(1, "temperature_c", 20.0)
            _persist_sensor_reading(2, "temperature_c", 25.0)

        db = TestingSessionLocal()
        node_ids = {r.node_id for r in db.query(SensorReadingDB).all()}
        db.close()
        assert node_ids == {1, 2}


# -- Sensor callbacks (on_temperature, on_humidity, on_context) ----------------

class TestSensorCallbacks:
    def test_temperature_callback_converts_raw_and_persists(self):
        with patch("app.main.SessionLocal", TestingSessionLocal):
            _register_sensor_callbacks([1])
            cb = _subscribers[(1, "1/1026/0")][0]
            asyncio.run(cb(1, "1/1026/0", 2150))

        db = TestingSessionLocal()
        row = db.query(SensorReadingDB).filter_by(sensor_type="temperature_c").first()
        db.close()

        assert row is not None
        assert row.value == pytest.approx(21.5)

    def test_humidity_callback_converts_raw_and_persists(self):
        with patch("app.main.SessionLocal", TestingSessionLocal):
            _register_sensor_callbacks([1])
            cb = _subscribers[(1, "2/1029/0")][0]
            asyncio.run(cb(1, "2/1029/0", 5940))

        db = TestingSessionLocal()
        row = db.query(SensorReadingDB).filter_by(sensor_type="humidity_rh").first()
        db.close()

        assert row is not None
        assert row.value == pytest.approx(59.4)

    def test_context_callback_persists_class_id(self):
        with patch("app.main.SessionLocal", TestingSessionLocal):
            _register_sensor_callbacks([1])
            cb = _subscribers[(1, "2/1029/1")][0]
            asyncio.run(cb(1, "2/1029/1", 2))

        db = TestingSessionLocal()
        row = db.query(SensorReadingDB).filter_by(sensor_type="context").first()
        db.close()

        assert row is not None
        assert row.value == pytest.approx(2.0)

    def test_temperature_callback_ignores_non_numeric(self):
        with patch("app.main.SessionLocal", TestingSessionLocal):
            _register_sensor_callbacks([1])
            cb = _subscribers[(1, "1/1026/0")][0]
            asyncio.run(cb(1, "1/1026/0", "not_a_number"))

        db = TestingSessionLocal()
        assert db.query(SensorReadingDB).count() == 0
        db.close()

    def test_humidity_callback_ignores_none(self):
        with patch("app.main.SessionLocal", TestingSessionLocal):
            _register_sensor_callbacks([1])
            cb = _subscribers[(1, "2/1029/0")][0]
            asyncio.run(cb(1, "2/1029/0", None))

        db = TestingSessionLocal()
        assert db.query(SensorReadingDB).count() == 0
        db.close()

    def test_context_callback_ignores_non_numeric(self):
        with patch("app.main.SessionLocal", TestingSessionLocal):
            _register_sensor_callbacks([1])
            cb = _subscribers[(1, "2/1029/1")][0]
            asyncio.run(cb(1, "2/1029/1", "bad"))

        db = TestingSessionLocal()
        assert db.query(SensorReadingDB).count() == 0
        db.close()

    def test_callbacks_registered_for_all_three_paths(self):
        _register_sensor_callbacks([1])
        assert (1, "1/1026/0") in _subscribers   # temperature
        assert (1, "2/1029/0") in _subscribers   # humidity
        assert (1, "2/1029/1") in _subscribers   # context

    def test_callbacks_registered_for_multiple_nodes(self):
        _register_sensor_callbacks([1, 2])
        for node_id in [1, 2]:
            assert (node_id, "1/1026/0") in _subscribers
            assert (node_id, "2/1029/0") in _subscribers
            assert (node_id, "2/1029/1") in _subscribers

    def test_context_callback_accepts_all_known_class_ids(self):
        for class_id in [0, 1, 2]:
            _subscribers.clear()
            with patch("app.main.SessionLocal", TestingSessionLocal):
                _register_sensor_callbacks([1])
                cb = _subscribers[(1, "2/1029/1")][0]
                asyncio.run(cb(1, "2/1029/1", class_id))

            db = TestingSessionLocal()
            row = db.query(SensorReadingDB).filter_by(sensor_type="context").first()
            db.close()
            
            assert row.value == pytest.approx(float(class_id))
            db2 = TestingSessionLocal()
            db2.query(SensorReadingDB).delete()
            db2.commit()
            db2.close()
