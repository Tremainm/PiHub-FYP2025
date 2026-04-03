"""
Tests for matter_ws command wrappers (get_nodes, remove_node, turn_on, etc.)
and _ws_call error handling.

Command functions are tested by patching _ws_call with AsyncMock, so no real
WebSocket connection is needed. asyncio.run() is used to drive the async functions
from synchronous pytest test functions.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

import app.matter_ws as ws_module
from app.matter_ws import (
    _ws_call,
    get_nodes,
    remove_node,
    set_wifi_credentials,
    commission_with_code,
    turn_on,
    turn_off,
    toggle,
    set_brightness,
    set_color_xy,
    CLUSTER_ON_OFF,
    CLUSTER_LEVEL_CONTROL,
    CLUSTER_COLOR_CONTROL,
)


@pytest.fixture(autouse=True)
def reset_ws_state():
    """Ensure _ws is None and _pending is empty before every test."""
    ws_module._ws = None
    ws_module._pending.clear()
    yield
    ws_module._ws = None
    ws_module._pending.clear()


# -- _ws_call: ConnectionError when not connected ------------------------------

def test_ws_call_raises_connection_error_when_ws_is_none():
    with pytest.raises(ConnectionError, match="Not connected"):
        asyncio.run(_ws_call("any_command"))


def test_ws_call_connection_error_message_mentions_background_listener():
    with pytest.raises(ConnectionError, match="start_background_listener"):
        asyncio.run(_ws_call("any_command"))


# -- get_nodes -----------------------------------------------------------------

def test_get_nodes_calls_ws_call_with_correct_command():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value=[])) as mock:
        asyncio.run(get_nodes())
    mock.assert_called_once_with("get_nodes")


def test_get_nodes_returns_result():
    expected = [{"node_id": 1}, {"node_id": 2}]
    with patch("app.matter_ws._ws_call", AsyncMock(return_value=expected)):
        result = asyncio.run(get_nodes())
    assert result == expected


# -- remove_node ---------------------------------------------------------------

def test_remove_node_passes_node_id():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(remove_node(3))
    mock.assert_called_once_with("remove_node", {"node_id": 3})


def test_remove_node_different_ids():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(remove_node(99))
    assert mock.call_args[0][1]["node_id"] == 99


# -- set_wifi_credentials ------------------------------------------------------

def test_set_wifi_credentials_sends_ssid_and_password():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_wifi_credentials("MyNet", "pass123"))
    mock.assert_called_once_with("set_wifi_credentials", {
        "ssid": "MyNet",
        "credentials": "pass123",
    })


def test_set_wifi_credentials_uses_credentials_key_not_password():
    # python-matter-server requires "credentials", not "password"
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_wifi_credentials("Net", "secret"))
    payload = mock.call_args[0][1]
    assert "credentials" in payload
    assert "password" not in payload


# -- commission_with_code ------------------------------------------------------

def test_commission_with_code_sends_code_and_defaults():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(commission_with_code("MT:Y.ABC1"))
    args_dict = mock.call_args[0][1]
    assert args_dict["code"] == "MT:Y.ABC1"
    assert args_dict["network_only"] is False
    assert "node_id" not in args_dict


def test_commission_with_code_includes_node_id_when_provided():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(commission_with_code("MT:Y.ABC1", node_id=5))
    assert mock.call_args[0][1]["node_id"] == 5


def test_commission_with_code_network_only_flag():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(commission_with_code("MT:Y.ABC1", network_only=True))
    assert mock.call_args[0][1]["network_only"] is True


def test_commission_uses_180s_timeout():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(commission_with_code("MT:Y.ABC1"))
    assert mock.call_args.kwargs.get("timeout") == 180.0


# -- turn_on / turn_off / toggle -----------------------------------------------

def test_turn_on_sends_on_command_to_on_off_cluster():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(turn_on(1))
    cmd_args = mock.call_args[0][1]
    assert cmd_args["command_name"] == "On"
    assert cmd_args["cluster_id"] == CLUSTER_ON_OFF
    assert cmd_args["node_id"] == 1


def test_turn_on_default_endpoint_is_1():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(turn_on(1))
    assert mock.call_args[0][1]["endpoint_id"] == 1


def test_turn_off_sends_off_command():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(turn_off(1))
    assert mock.call_args[0][1]["command_name"] == "Off"
    assert mock.call_args[0][1]["cluster_id"] == CLUSTER_ON_OFF


def test_toggle_sends_toggle_command():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(toggle(1))
    assert mock.call_args[0][1]["command_name"] == "Toggle"


# -- set_brightness ------------------------------------------------------------

def test_set_brightness_sends_move_to_level_with_on_off():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_brightness(1, 128))
    cmd_args = mock.call_args[0][1]
    assert cmd_args["command_name"] == "MoveToLevelWithOnOff"
    assert cmd_args["cluster_id"] == CLUSTER_LEVEL_CONTROL
    assert cmd_args["payload"]["level"] == 128


def test_set_brightness_clamps_zero_to_one():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_brightness(1, 0))
    assert mock.call_args[0][1]["payload"]["level"] == 1


def test_set_brightness_clamps_overflow_to_254():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_brightness(1, 300))
    assert mock.call_args[0][1]["payload"]["level"] == 254


def test_set_brightness_allows_max_value():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_brightness(1, 254))
    assert mock.call_args[0][1]["payload"]["level"] == 254


def test_set_brightness_includes_transition_time():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_brightness(1, 200, transition_time=10))
    assert mock.call_args[0][1]["payload"]["transitionTime"] == 10


def test_set_brightness_default_transition_is_zero():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_brightness(1, 128))
    assert mock.call_args[0][1]["payload"]["transitionTime"] == 0


# -- set_color_xy --------------------------------------------------------------

def test_set_color_xy_sends_move_to_color_command():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_color_xy(1, 0.7, 0.3))
    cmd_args = mock.call_args[0][1]
    assert cmd_args["command_name"] == "MoveToColor"
    assert cmd_args["cluster_id"] == CLUSTER_COLOR_CONTROL


def test_set_color_xy_scales_floats_to_65536_range():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_color_xy(1, 0.7, 0.3))
    payload = mock.call_args[0][1]["payload"]
    assert payload["colorX"] == int(0.7 * 65536)
    assert payload["colorY"] == int(0.3 * 65536)


def test_set_color_xy_zero_coordinates():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_color_xy(1, 0.0, 0.0))
    payload = mock.call_args[0][1]["payload"]
    assert payload["colorX"] == 0
    assert payload["colorY"] == 0


def test_set_color_xy_includes_transition_time():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_color_xy(1, 0.5, 0.4, transition_time=5))
    assert mock.call_args[0][1]["payload"]["transitionTime"] == 5


def test_set_color_xy_default_transition_is_zero():
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_color_xy(1, 0.5, 0.4))
    assert mock.call_args[0][1]["payload"]["transitionTime"] == 0


def test_set_color_xy_red_preset():
    # Red: x=0.700, y=0.299
    with patch("app.matter_ws._ws_call", AsyncMock(return_value={})) as mock:
        asyncio.run(set_color_xy(1, 0.700, 0.299))
    payload = mock.call_args[0][1]["payload"]
    assert payload["colorX"] == int(0.700 * 65536)
    assert payload["colorY"] == int(0.299 * 65536)
