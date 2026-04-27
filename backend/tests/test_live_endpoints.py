"""
Tests for live-data endpoints and LED control.
No real WebSocket or DB is needed - matter_ws functions are mocked.
"""
from unittest.mock import AsyncMock, patch


# -- Live sensor cache ---------------------------------------------------------

def test_live_sensors_no_cache_returns_404(client):
    mock = {"temperature_c": None, "humidity_rh": None, "context_class": None, "context_label": None}
    with patch("app.main.get_cached_sensor_data", return_value=mock):   # fake get_cached_sensor_data using mock data
        r = client.get("/api/matter/nodes/1/sensors/live")
    assert r.status_code == 404


def test_live_sensors_returns_data(client):
    mock = {"temperature_c": 21.5, "humidity_rh": 55.0, "context_class": 1, "context_label": "NORMAL"}
    with patch("app.main.get_cached_sensor_data", return_value=mock):
        r = client.get("/api/matter/nodes/1/sensors/live")
    assert r.status_code == 200
    body = r.json()
    assert body["node_id"] == 1
    assert body["temperature_c"] == 21.5
    assert body["humidity_rh"] == 55.0


def test_live_sensors_partial_data_ok(client):
    # Only temperature cached, humidity still None - should return 200
    mock = {"temperature_c": 21.5, "humidity_rh": None, "context_class": None, "context_label": None}
    with patch("app.main.get_cached_sensor_data", return_value=mock):
        r = client.get("/api/matter/nodes/1/sensors/live")
    assert r.status_code == 200


def test_live_temperature_no_cache_returns_404(client):
    with patch("app.main.get_cached_temperature", return_value=None):
        r = client.get("/api/matter/nodes/1/temperature/live")
    assert r.status_code == 404


def test_live_temperature_returns_value(client):
    with patch("app.main.get_cached_temperature", return_value=22.3):
        r = client.get("/api/matter/nodes/1/temperature/live")
    assert r.status_code == 200
    assert r.json()["temperature_c"] == 22.3
    assert r.json()["node_id"] == 1


def test_live_humidity_no_cache_returns_404(client):
    with patch("app.main.get_cached_humidity", return_value=None):
        r = client.get("/api/matter/nodes/1/humidity/live")
    assert r.status_code == 404


def test_live_humidity_returns_value(client):
    with patch("app.main.get_cached_humidity", return_value=60.5):
        r = client.get("/api/matter/nodes/1/humidity/live")
    assert r.status_code == 200
    assert r.json()["humidity_rh"] == 60.5


def test_live_light_state_no_cache_returns_404(client):
    mock = {"on": None, "brightness": None, "color_xy": None}
    with patch("app.main.get_cached_light_state", return_value=mock):
        r = client.get("/api/matter/nodes/1/state/live")
    assert r.status_code == 404


def test_live_light_state_returns_full_state(client):
    mock = {"on": True, "brightness": 200, "color_xy": {"x": 0.7, "y": 0.3}}
    with patch("app.main.get_cached_light_state", return_value=mock):
        r = client.get("/api/matter/nodes/1/state/live")
    assert r.status_code == 200
    body = r.json()
    assert body["on"] is True
    assert body["brightness"] == 200
    assert body["color_xy"] == {"x": 0.7, "y": 0.3}


def test_live_light_state_off(client):
    mock = {"on": False, "brightness": 0, "color_xy": None}
    with patch("app.main.get_cached_light_state", return_value=mock):
        r = client.get("/api/matter/nodes/1/state/live")
    assert r.status_code == 200
    assert r.json()["on"] is False


# -- LED control ---------------------------------------------------------------

def test_light_on(client):
    with patch("app.main.turn_on", AsyncMock(return_value={"result": "ok"})) as mock:
        r = client.post("/api/matter/nodes/1/on")
    assert r.status_code == 200
    mock.assert_called_once_with(1)


def test_light_off(client):
    with patch("app.main.turn_off", AsyncMock(return_value={"result": "ok"})) as mock:
        r = client.post("/api/matter/nodes/1/off")
    assert r.status_code == 200
    mock.assert_called_once_with(1)


def test_light_toggle(client):
    with patch("app.main.toggle", AsyncMock(return_value={"result": "ok"})) as mock:
        r = client.post("/api/matter/nodes/1/toggle")
    assert r.status_code == 200
    mock.assert_called_once_with(1)


def test_set_brightness_default_transition(client):
    with patch("app.main.set_brightness", AsyncMock(return_value={"result": "ok"})) as mock:
        r = client.post("/api/matter/nodes/1/brightness", json={"level": 128})
    assert r.status_code == 200
    mock.assert_called_once_with(1, 128, 0)


def test_set_brightness_with_transition(client):
    with patch("app.main.set_brightness", AsyncMock(return_value={"result": "ok"})) as mock:
        r = client.post("/api/matter/nodes/1/brightness", json={"level": 200, "transition_time": 10})
    assert r.status_code == 200
    mock.assert_called_once_with(1, 200, 10)


def test_set_brightness_missing_level_returns_422(client):
    r = client.post("/api/matter/nodes/1/brightness", json={})
    assert r.status_code == 422


def test_set_color_xy_default_transition(client):
    with patch("app.main.set_color_xy", AsyncMock(return_value={"result": "ok"})) as mock:
        r = client.post("/api/matter/nodes/1/color/xy", json={"x": 0.7, "y": 0.3})
    assert r.status_code == 200
    mock.assert_called_once_with(1, 0.7, 0.3, 0)


def test_set_color_xy_with_transition(client):
    with patch("app.main.set_color_xy", AsyncMock(return_value={"result": "ok"})) as mock:
        r = client.post("/api/matter/nodes/1/color/xy", json={"x": 0.136, "y": 0.040, "transition_time": 5})
    assert r.status_code == 200
    mock.assert_called_once_with(1, 0.136, 0.040, 5)


def test_set_color_xy_missing_fields_returns_422(client):
    r = client.post("/api/matter/nodes/1/color/xy", json={"x": 0.5})
    assert r.status_code == 422


# -- Node management -----------------------------------------------------------

def test_get_nodes(client):
    with patch("app.main.get_nodes", AsyncMock(return_value=[{"node_id": 1}, {"node_id": 2}])):
        r = client.get("/api/matter/nodes")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_remove_node(client):
    with patch("app.main.remove_node", AsyncMock(return_value={"result": "ok"})) as mock:
        r = client.delete("/api/matter/nodes/3")
    assert r.status_code == 200
    mock.assert_called_once_with(3)


# -- Commissioning -------------------------------------------------------------

def test_set_wifi_credentials(client):
    with patch("app.main.set_wifi_credentials", AsyncMock(return_value={"result": "ok"})) as mock:
        r = client.post("/api/matter/wifi", json={"ssid": "MyNet", "password": "secret"})
    assert r.status_code == 200
    mock.assert_called_once_with("MyNet", "secret")


def test_commission_device_minimal(client):
    with patch("app.main.commission_with_code", AsyncMock(return_value={"result": "ok"})) as mock:
        r = client.post("/api/matter/commission", json={"code": "MT:Y.ABC1"})
    assert r.status_code == 200
    mock.assert_called_once_with("MT:Y.ABC1", node_id=None, network_only=False)


def test_commission_device_with_node_id_and_network_only(client):
    with patch("app.main.commission_with_code", AsyncMock(return_value={"result": "ok"})) as mock:
        r = client.post("/api/matter/commission", json={"code": "MT:Y.ABC1", "node_id": 5, "network_only": True})
    assert r.status_code == 200
    mock.assert_called_once_with("MT:Y.ABC1", node_id=5, network_only=True)


def test_commission_missing_code_returns_422(client):
    r = client.post("/api/matter/commission", json={})
    assert r.status_code == 422
