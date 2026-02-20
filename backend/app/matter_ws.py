# app/matter_ws.py
import asyncio
import json
import os
import uuid
from typing import Any, Optional

import websockets

MATTER_WS_URL = os.getenv("MATTER_WS_URL", "ws://127.0.0.1:5580/ws")

# Matter spec constants
CLUSTER_TEMPERATURE_MEASUREMENT = 0x0402
ATTRIBUTE_MEASURED_VALUE = 0x0000

CLUSTER_ON_OFF = 0x0006
COMMAND_ON = "On"
COMMAND_OFF = "Off"
COMMAND_TOGGLE = "Toggle"
CLUSTER_LEVEL_CONTROL = 0x0008
CLUSTER_COLOR_CONTROL = 0x0300


async def _ws_call(command: str, args: Optional[dict[str, Any]] = None, timeout: float = 60.0) -> dict[str, Any]:
    """
    Minimal one-shot call into python-matter-server.
    Opens a connection, sends {message_id, command, args}, waits for matching response, closes.
    """
    message_id = uuid.uuid4().hex
    payload: dict[str, Any] = {"message_id": message_id, "command": command}
    if args is not None:
        payload["args"] = args

    async with websockets.connect(MATTER_WS_URL, ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps(payload))

        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            msg = json.loads(raw)

            # Responses to our call include the same message_id
            if msg.get("message_id") == message_id:
                return msg


# def call(command: str, args: Optional[dict[str, Any]] = None, timeout: float = 60.0) -> dict[str, Any]:
#     """
#     Sync wrapper so I can keep my current synchronous FastAPI endpoints.
#     """
#     return asyncio.run(_ws_call(command, args=args, timeout=timeout))

async def send_command(node_id: int, endpoint_id: int, cluster_id: int, command_id: int, payload: Optional[dict] = None) -> dict[str, Any]:
    """
    Send a cluster command to a Matter node.
    
    node_id:     the commissioned node's ID (3)
    endpoint_id: which endpoint on the device (light is typically 1)
    cluster_id:  which cluster to target (e.g. 0x0006 for OnOff)
    command_id:  which command within the cluster ("On"=On, "Off"=Off, "Toggle"=Toggle)
    payload:     optional dict of command fields (not needed for On/Off/Toggle)
    
    python-matter-server's device_command expects these exact field names.
    """
    args: dict[str, Any] = {
        "node_id": node_id,
        "endpoint_id": endpoint_id,
        "cluster_id": cluster_id,
        "command_name": command_id,
        "payload": payload or {},
    }
    return await _ws_call("device_command", args)


async def turn_on(node_id: int, endpoint_id: int = 1) -> dict[str, Any]:
    return await send_command(node_id, endpoint_id, CLUSTER_ON_OFF, COMMAND_ON)


async def turn_off(node_id: int, endpoint_id: int = 1) -> dict[str, Any]:
    return await send_command(node_id, endpoint_id, CLUSTER_ON_OFF, COMMAND_OFF)


async def toggle(node_id: int, endpoint_id: int = 1) -> dict[str, Any]:
    return await send_command(node_id, endpoint_id, CLUSTER_ON_OFF, COMMAND_TOGGLE)

async def set_brightness(node_id: int, level: int, endpoint_id: int = 1) -> dict[str, Any]:
    """
    Set LED brightness using the LevelControl cluster's MoveToLevel command.

    level: integer 0-254 (0 = off, 254 = full brightness)
           Note: 0 doesn't turn off the OnOff state, it just sets level to minimum.
           Use turn_off() for a clean off.
    transition_time: in tenths of a second (0 = immediate)

    The MoveToLevel command payload requires:
      - level: the target brightness (0-254)
      - transition_time: how long to fade (0 = instant)
      - option_mask / option_override: standard LevelControl options, 0 for defaults
    """
    return await send_command(
        node_id,
        endpoint_id,
        CLUSTER_LEVEL_CONTROL,
        "MoveToLevel",
        {
            "level": max(0, min(254, level)),  # clamp to valid range
            "transitionTime": 0,
            "optionsMask": 0,
            "optionsOverride": 0,
        }
    )


async def set_color_xy(node_id: int, x: float, y: float, endpoint_id: int = 1) -> dict[str, Any]:
    """
    Set LED colour using CIE 1931 XY colour space via the MoveToColor command.

    x, y: floats between 0.0 and 1.0 representing the CIE XY chromaticity.
    Matter expects these multiplied by 65536 as integers.

    Some useful XY values:
      Red:   x=0.700, y=0.299
      Green: x=0.172, y=0.747
      Blue:  x=0.136, y=0.040
      Warm white: x=0.450, y=0.408
      Cool white: x=0.313, y=0.329
    """
    return await send_command(
        node_id,
        endpoint_id,
        CLUSTER_COLOR_CONTROL,
        "MoveToColor",
        {
            "colorX": int(x * 65536),
            "colorY": int(y * 65536),
            "transitionTime": 0,
            "optionsMask": 0,
            "optionsOverride": 0,
        }
    )

async def set_wifi_credentials(ssid: str, password: str) -> dict[str, Any]:
    # python-matter-server expects "credentials" for the password field.
    return await _ws_call("set_wifi_credentials", {"ssid": ssid, "credentials": password})


async def commission_with_code(code: str, node_id: Optional[int] = None) -> dict[str, Any]:
    args: dict[str, Any] = {"code": code, "network_only": False}
    if node_id is not None:
        args["node_id"] = node_id
    # BLE commissioning happens automatically if the host has BLE available.
    return await _ws_call("commission_with_code", args, timeout=180.0)


async def get_nodes() -> dict[str, Any]:
    return await _ws_call("get_nodes")

async def get_node(node_id: int) -> dict[str, Any]:
    return await _ws_call("get_node", {"node_id": node_id})

def _find_temp_measuredvalue(node_payload: Any) -> Optional[float]:
    """
    python-matter-server get_node returns:
      result.attributes is a dict with keys like "1/1026/0" => 1940
    where:
      endpoint 1, cluster 1026 (TemperatureMeasurement), attribute 0 (MeasuredValue)
      value is in 0.01°C units.
    """
    if not isinstance(node_payload, dict):
        return None

    # unwrap common wrapper shapes
    attrs = None
    if "result" in node_payload and isinstance(node_payload["result"], dict):
        attrs = node_payload["result"].get("attributes")
    if attrs is None and "attributes" in node_payload:
        attrs = node_payload.get("attributes")

    if not isinstance(attrs, dict):
        return None

    raw = attrs.get("1/1026/0")
    if isinstance(raw, (int, float)):
        return float(raw) / 100.0

    return None

async def read_temperature_c(node_id: int) -> Optional[float]:
    resp = await get_node(node_id)
    return _find_temp_measuredvalue(resp)

# def read_humidity_rh(node_id: int) -> Optional[float]:
#     resp = get_node(node_id)
#     attrs = resp.get("result", {}).get("attributes", {})
#     raw = attrs.get("2/1029/0")
#     if isinstance(raw, (int, float)):
#         return float(raw) / 100.0
#     return None

