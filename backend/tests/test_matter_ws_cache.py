"""
Tests for the pure-Python cache helpers in matter_ws.py.
No WebSocket connection is needed — we manipulate _attribute_cache directly.
"""
import pytest
from app.matter_ws import (
    _attribute_cache,
    _subscribers,
    _cache_node,
    _evict_node,
    _find_cached,
    register_callback,
    get_cached_temperature,
    get_cached_humidity,
    get_cached_on_off,
    get_cached_brightness,
    get_cached_color_xy,
    get_cached_sensor_data,
    get_cached_light_state,
    get_cached_context,
    CONTEXT_LABELS,
    CLUSTER_TEMPERATURE,
    CLUSTER_HUMIDITY,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Reset module-level dicts before and after every test in this file."""
    _attribute_cache.clear()
    _subscribers.clear()
    yield
    _attribute_cache.clear()
    _subscribers.clear()


# -- CONTEXT_LABELS ------------------------------------------------------------

class TestContextLabels:
    def test_heating_on(self):
        assert CONTEXT_LABELS[0] == "HEATING_ON"

    def test_normal(self):
        assert CONTEXT_LABELS[1] == "NORMAL"

    def test_window_open(self):
        assert CONTEXT_LABELS[2] == "WINDOW_OPEN"


# -- _cache_node ---------------------------------------------------------------

class TestCacheNode:
    def test_populates_cache(self):
        _cache_node({"node_id": 1, "attributes": {"1/1026/0": 2150, "2/1029/0": 5940}})
        assert _attribute_cache[(1, "1/1026/0")] == 2150
        assert _attribute_cache[(1, "2/1029/0")] == 5940

    def test_ignores_missing_node_id(self):
        _cache_node({"attributes": {"1/1026/0": 2150}})
        assert (None, "1/1026/0") not in _attribute_cache

    def test_ignores_non_dict_attributes(self):
        _cache_node({"node_id": 1, "attributes": "not_a_dict"})
        # Should not raise, cache unchanged

    def test_multiple_nodes_cached_independently(self):
        _cache_node({"node_id": 1, "attributes": {"1/1026/0": 2000}})
        _cache_node({"node_id": 2, "attributes": {"1/1026/0": 2500}})
        assert _attribute_cache[(1, "1/1026/0")] == 2000
        assert _attribute_cache[(2, "1/1026/0")] == 2500

    def test_overwrites_existing_entry(self):
        _cache_node({"node_id": 1, "attributes": {"1/1026/0": 2000}})
        _cache_node({"node_id": 1, "attributes": {"1/1026/0": 2500}})
        assert _attribute_cache[(1, "1/1026/0")] == 2500


# -- _evict_node ---------------------------------------------------------------

class TestEvictNode:
    def test_removes_all_entries_for_node(self):
        _attribute_cache[(1, "1/1026/0")] = 2150
        _attribute_cache[(1, "2/1029/0")] = 5940
        _attribute_cache[(2, "1/1026/0")] = 1800
        _evict_node(1)
        assert (1, "1/1026/0") not in _attribute_cache
        assert (1, "2/1029/0") not in _attribute_cache

    def test_leaves_other_nodes_untouched(self):
        _attribute_cache[(1, "1/1026/0")] = 2150
        _attribute_cache[(2, "1/1026/0")] = 1800
        _evict_node(1)
        assert _attribute_cache[(2, "1/1026/0")] == 1800

    def test_evict_nonexistent_node_does_not_raise(self):
        _evict_node(999)


# -- _find_cached --------------------------------------------------------------

class TestFindCached:
    def test_finds_matching_attribute(self):
        _attribute_cache[(1, "1/1026/0")] = 2150
        assert _find_cached(1, CLUSTER_TEMPERATURE, 0) == 2150

    def test_returns_none_when_missing(self):
        assert _find_cached(99, CLUSTER_TEMPERATURE, 0) is None

    def test_ignores_wrong_node_id(self):
        _attribute_cache[(2, "1/1026/0")] = 2150
        assert _find_cached(1, CLUSTER_TEMPERATURE, 0) is None

    def test_ignores_wrong_cluster(self):
        _attribute_cache[(1, "1/1026/0")] = 2150
        assert _find_cached(1, CLUSTER_HUMIDITY, 0) is None

    def test_finds_specific_attribute_id(self):
        # MinMeasuredValue (attribute 1) on humidity cluster
        _attribute_cache[(1, "2/1029/1")] = 1
        assert _find_cached(1, CLUSTER_HUMIDITY, 1) == 1

    def test_finds_across_any_endpoint(self):
        # Endpoint 3 instead of 1
        _attribute_cache[(1, "3/1026/0")] = 3000
        assert _find_cached(1, CLUSTER_TEMPERATURE, 0) == 3000


# -- get_cached_temperature ----------------------------------------------------

class TestGetCachedTemperature:
    def test_returns_none_when_empty(self):
        assert get_cached_temperature(1) is None

    def test_converts_matter_raw_to_celsius(self):
        _attribute_cache[(1, "1/1026/0")] = 2150
        assert get_cached_temperature(1) == pytest.approx(21.5)

    def test_converts_negative_temperature(self):
        _attribute_cache[(1, "1/1026/0")] = -500
        assert get_cached_temperature(1) == pytest.approx(-5.0)

    def test_accepts_float_raw_value(self):
        _attribute_cache[(1, "1/1026/0")] = 2200.0
        assert get_cached_temperature(1) == pytest.approx(22.0)

    def test_zero_temperature(self):
        _attribute_cache[(1, "1/1026/0")] = 0
        assert get_cached_temperature(1) == pytest.approx(0.0)


# -- get_cached_humidity -------------------------------------------------------

class TestGetCachedHumidity:
    def test_returns_none_when_empty(self):
        assert get_cached_humidity(1) is None

    def test_converts_matter_raw_to_percent(self):
        _attribute_cache[(1, "2/1029/0")] = 5940
        assert get_cached_humidity(1) == pytest.approx(59.4)

    def test_zero_humidity(self):
        _attribute_cache[(1, "2/1029/0")] = 0
        assert get_cached_humidity(1) == pytest.approx(0.0)

    def test_full_humidity(self):
        _attribute_cache[(1, "2/1029/0")] = 10000
        assert get_cached_humidity(1) == pytest.approx(100.0)


# -- get_cached_on_off ---------------------------------------------------------

class TestGetCachedOnOff:
    def test_returns_none_when_empty(self):
        assert get_cached_on_off(1) is None

    def test_returns_true_when_on(self):
        _attribute_cache[(1, "1/6/0")] = True
        assert get_cached_on_off(1) is True

    def test_returns_false_when_off(self):
        _attribute_cache[(1, "1/6/0")] = False
        assert get_cached_on_off(1) is False


# -- get_cached_brightness -----------------------------------------------------

class TestGetCachedBrightness:
    def test_returns_none_when_empty(self):
        assert get_cached_brightness(1) is None

    def test_returns_brightness_value(self):
        _attribute_cache[(1, "1/8/0")] = 200
        assert get_cached_brightness(1) == 200

    def test_returns_zero_brightness(self):
        _attribute_cache[(1, "1/8/0")] = 0
        assert get_cached_brightness(1) == 0

    def test_max_brightness(self):
        _attribute_cache[(1, "1/8/0")] = 254
        assert get_cached_brightness(1) == 254


# -- get_cached_color_xy -------------------------------------------------------

class TestGetCachedColorXY:
    def test_returns_none_when_empty(self):
        assert get_cached_color_xy(1) is None

    def test_returns_none_when_only_x_present(self):
        _attribute_cache[(1, "1/768/3")] = 45875
        assert get_cached_color_xy(1) is None

    def test_returns_none_when_only_y_present(self):
        _attribute_cache[(1, "1/768/4")] = 19595
        assert get_cached_color_xy(1) is None

    def test_converts_raw_to_float_coordinates(self):
        # Red: x≈0.700, y≈0.299 in Matter scale (×65536)
        _attribute_cache[(1, "1/768/3")] = 45875   # 0.700 * 65536
        _attribute_cache[(1, "1/768/4")] = 19595   # 0.299 * 65536
        result = get_cached_color_xy(1)
        assert result is not None
        assert result["x"] == pytest.approx(0.700, abs=0.002)
        assert result["y"] == pytest.approx(0.299, abs=0.002)

    def test_warm_white_coordinates(self):
        # Warm white: x=0.450, y=0.408
        _attribute_cache[(1, "1/768/3")] = int(0.450 * 65536)
        _attribute_cache[(1, "1/768/4")] = int(0.408 * 65536)
        result = get_cached_color_xy(1)
        assert result["x"] == pytest.approx(0.450, abs=0.002)
        assert result["y"] == pytest.approx(0.408, abs=0.002)


# -- get_cached_context --------------------------------------------------------

class TestGetCachedContext:
    def test_returns_none_fields_when_empty(self):
        result = get_cached_context(1)
        assert result["context_class"] is None
        assert result["context_label"] is None

    def test_heating_on(self):
        _attribute_cache[(1, "2/1029/1")] = 0
        result = get_cached_context(1)
        assert result["context_class"] == 0
        assert result["context_label"] == "HEATING_ON"

    def test_normal(self):
        _attribute_cache[(1, "2/1029/1")] = 1
        result = get_cached_context(1)
        assert result["context_class"] == 1
        assert result["context_label"] == "NORMAL"

    def test_window_open(self):
        _attribute_cache[(1, "2/1029/1")] = 2
        result = get_cached_context(1)
        assert result["context_class"] == 2
        assert result["context_label"] == "WINDOW_OPEN"

    def test_unknown_class_id(self):
        _attribute_cache[(1, "2/1029/1")] = 99
        result = get_cached_context(1)
        assert result["context_label"] == "UNKNOWN"


# -- get_cached_sensor_data ----------------------------------------------------

class TestGetCachedSensorData:
    def test_all_none_when_empty(self):
        data = get_cached_sensor_data(1)
        assert data["temperature_c"] is None
        assert data["humidity_rh"] is None
        assert data["context_class"] is None

    def test_returns_temperature_and_humidity(self):
        _attribute_cache[(1, "1/1026/0")] = 2150
        _attribute_cache[(1, "2/1029/0")] = 5940
        data = get_cached_sensor_data(1)
        assert data["temperature_c"] == pytest.approx(21.5)
        assert data["humidity_rh"] == pytest.approx(59.4)

    def test_includes_context(self):
        _attribute_cache[(1, "2/1029/1")] = 1
        data = get_cached_sensor_data(1)
        assert data["context_label"] == "NORMAL"


# -- get_cached_light_state ----------------------------------------------------

class TestGetCachedLightState:
    def test_all_none_when_empty(self):
        state = get_cached_light_state(1)
        assert state["on"] is None
        assert state["brightness"] is None
        assert state["color_xy"] is None

    def test_returns_on_off_and_brightness(self):
        _attribute_cache[(1, "1/6/0")] = True
        _attribute_cache[(1, "1/8/0")] = 200
        state = get_cached_light_state(1)
        assert state["on"] is True
        assert state["brightness"] == 200

    def test_returns_full_state(self):
        _attribute_cache[(1, "1/6/0")] = True
        _attribute_cache[(1, "1/8/0")] = 200
        _attribute_cache[(1, "1/768/3")] = int(0.700 * 65536)
        _attribute_cache[(1, "1/768/4")] = int(0.299 * 65536)
        state = get_cached_light_state(1)
        assert state["on"] is True
        assert state["brightness"] == 200
        assert state["color_xy"] is not None


# -- register_callback ---------------------------------------------------------

class TestRegisterCallback:
    def test_registers_single_callback(self):
        async def my_cb(node_id, path, value):
            pass

        register_callback(1, "1/1026/0", my_cb)
        assert my_cb in _subscribers[(1, "1/1026/0")]

    def test_multiple_callbacks_on_same_key(self):
        async def cb1(node_id, path, value): pass
        async def cb2(node_id, path, value): pass

        register_callback(1, "1/1026/0", cb1)
        register_callback(1, "1/1026/0", cb2)
        subs = _subscribers[(1, "1/1026/0")]
        assert cb1 in subs and cb2 in subs

    def test_different_paths_are_separate(self):
        async def temp_cb(node_id, path, value): pass
        async def hum_cb(node_id, path, value): pass

        register_callback(1, "1/1026/0", temp_cb)
        register_callback(1, "2/1029/0", hum_cb)
        assert temp_cb not in _subscribers.get((1, "2/1029/0"), [])
        assert hum_cb not in _subscribers.get((1, "1/1026/0"), [])
