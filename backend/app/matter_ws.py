import asyncio
import json
import os
import uuid
from typing import Any, Optional, Callable

import websockets
import logging

logger = logging.getLogger(__name__)

MATTER_WS_URL = os.getenv("MATTER_WS_URL", "ws://127.0.0.1:5580/ws")

# In-memory cache for latest sensor values, keyed by (node_id, attribute_path)
# e.g. { (1, "1/1026/0"): 1820, (1, "1/1029/0"): 5940 }
_attribute_cache: dict[tuple[int, str], Any] = {}

# Registered callbacks: (node_id, attribute_path) -> list of async callables
_subscribers: dict[tuple[int, str], list[Callable]] = {}

# Matter attribute paths
ATTR_TEMPERATURE = "1/1026/0"   # endpoint 1, cluster 0x0402, attribute 0x0000
ATTR_HUMIDITY    = "1/1029/0"   # endpoint 1, cluster 0x0405, attribute 0x0000

# Matter spec constants
CLUSTER_TEMPERATURE_MEASUREMENT = 0x0402
CLUSTER_HUMIDITY_MEASUREMENT = 0x0405
ATTRIBUTE_MEASURED_VALUE = 0x0000

CLUSTER_ON_OFF = 0x0006
COMMAND_ON = "On"
COMMAND_OFF = "Off"
COMMAND_TOGGLE = "Toggle"
CLUSTER_LEVEL_CONTROL = 0x0008
CLUSTER_COLOR_CONTROL = 0x0300

async def _background_listener():
    """
    Long-lived websocket connection to python-matter-server.

    start_listening returns an initial response shaped like:
    {
        "message_id": "...",
        "result": [ { node data dict }, { node data dict }, ... ]  <-- list of all nodes
    }

    After that, ongoing events arrive as:
    {
        "event": "attribute_updated",
        "data": { "node_id": 1, "attribute_path": "1/1026/0", "value": 1820 }
    }
    or:
    {
        "event": "node_updated",
        "data": { "node_id": 1, "attributes": { "1/1026/0": 1820, ... } }
    }
    """
    while True:
        try:
            async with websockets.connect(
                MATTER_WS_URL,
                ping_interval=20,
                ping_timeout=20
            ) as ws:
                logger.info("Background listener connected — sending start_listening")

                message_id = uuid.uuid4().hex
                await ws.send(json.dumps({
                    "message_id": message_id,
                    "command": "start_listening"
                }))

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    # --- Handle the initial start_listening response ---
                    # This comes back with the same message_id we sent,
                    # and result is a list of all currently known nodes.
                    if msg.get("message_id") == message_id:
                        nodes = msg.get("result", [])
                        if isinstance(nodes, list):
                            for node in nodes:
                                if not isinstance(node, dict):
                                    continue
                                node_id = node.get("node_id")
                                attributes = node.get("attributes", {})
                                if node_id is not None and isinstance(attributes, dict):
                                    for attr_path, value in attributes.items():
                                        _attribute_cache[(node_id, attr_path)] = value
                                    logger.debug(
                                        "Initial load: node=%s, %d attributes cached",
                                        node_id, len(attributes)
                                    )
                        continue  # done handling the initial response

                    # --- Handle ongoing events ---
                    event = msg.get("event")

                    if event == "attribute_updated":
                        # Single attribute changed on a node
                        data = msg.get("data", {})
                        if not isinstance(data, dict):
                            continue
                        node_id = data.get("node_id")
                        attr_path = data.get("attribute_path")
                        value = data.get("value")

                        if node_id is not None and attr_path is not None:
                            cache_key = (node_id, attr_path)
                            _attribute_cache[cache_key] = value
                            logger.debug(
                                "attribute_updated: node=%s path=%s value=%s",
                                node_id, attr_path, value
                            )
                            for callback in _subscribers.get(cache_key, []):
                                try:
                                    await callback(node_id, attr_path, value)
                                except Exception as e:
                                    logger.error("Callback error: %s", e)

                    elif event == "node_updated":
                        # Full attribute dump for a node (e.g. after reconnect)
                        data = msg.get("data", {})
                        if not isinstance(data, dict):
                            continue
                        node_id = data.get("node_id")
                        attributes = data.get("attributes", {})

                        if node_id is not None and isinstance(attributes, dict):
                            for attr_path, value in attributes.items():
                                _attribute_cache[(node_id, attr_path)] = value
                            logger.debug(
                                "node_updated: node=%s, %d attributes cached",
                                node_id, len(attributes)
                            )

        except (websockets.ConnectionClosed, OSError) as e:
            logger.warning(
                "Background listener disconnected: %s — reconnecting in 5s", e
            )
            await asyncio.sleep(5)


def start_background_listener():
    """
    Call this once on app startup to begin listening for attribute events.
    Uses asyncio.create_task so it runs concurrently with FastAPI.
    """
    asyncio.create_task(_background_listener())


def register_callback(node_id: int, attribute_path: str, callback: Callable):
    """
    Register an async callback to be fired when a specific attribute updates.

    Example:
        async def on_temp(node_id, path, value):
            print(f"Temperature changed: {value / 100}°C")

        register_callback(1, ATTR_TEMPERATURE, on_temp)
    """
    key = (node_id, attribute_path)
    if key not in _subscribers:
        _subscribers[key] = []
    _subscribers[key].append(callback)


def get_cached_temperature(node_id: int) -> Optional[float]:
    """Search cache for temperature cluster (0x0402) on any endpoint for this node."""
    for (nid, path), value in _attribute_cache.items():
        if nid != node_id:
            continue
        parts = path.split("/")
        if len(parts) == 3 and int(parts[1]) == CLUSTER_TEMPERATURE_MEASUREMENT and int(parts[2]) == 0:
            if isinstance(value, (int, float)):
                return float(value) / 100.0
    return None


def get_cached_humidity(node_id: int) -> Optional[float]:
    """Search cache for humidity cluster (0x0405) on any endpoint for this node."""
    for (nid, path), value in _attribute_cache.items():
        if nid != node_id:
            continue
        parts = path.split("/")
        if len(parts) == 3 and int(parts[1]) == CLUSTER_HUMIDITY_MEASUREMENT and int(parts[2]) == 0:
            if isinstance(value, (int, float)):
                return float(value) / 100.0
    return None


def get_cached_sensor_data(node_id: int) -> dict[str, Optional[float]]:
    """
    Returns both temperature and humidity from cache in one call.
    """
    return {
        "temperature_c": get_cached_temperature(node_id),
        "humidity_rh": get_cached_humidity(node_id),
    }

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

def _find_attribute(node_payload: dict, cluster_id: int, attribute_id: int = 0) -> Optional[Any]:
    """
    Search all endpoints in a node's attributes for a given cluster/attribute.
    Returns the value from the first matching endpoint, or None.

    This avoids hardcoding endpoint numbers since different devices
    may place clusters on different endpoints.
    The attribute key format is "endpoint/cluster/attribute".
    """
    attrs = None
    if "result" in node_payload and isinstance(node_payload["result"], dict):
        attrs = node_payload["result"].get("attributes")
    if attrs is None and "attributes" in node_payload:
        attrs = node_payload.get("attributes")

    if not isinstance(attrs, dict):
        return None

    # Search every key for matching cluster and attribute
    for key, value in attrs.items():
        parts = key.split("/")
        if len(parts) != 3:
            continue
        _, c, a = parts
        if int(c) == cluster_id and int(a) == attribute_id:
            return value

    return None

def _find_temp_measuredvalue(node_payload: Any) -> Optional[float]:
    raw = _find_attribute(node_payload, cluster_id=CLUSTER_TEMPERATURE_MEASUREMENT, attribute_id=ATTRIBUTE_MEASURED_VALUE)
    if isinstance(raw, (int, float)):
        return float(raw) / 100.0
    return None

def _find_humidity_measuredvalue(node_payload: Any) -> Optional[float]:
    raw = _find_attribute(node_payload, cluster_id=CLUSTER_HUMIDITY_MEASUREMENT, attribute_id=ATTRIBUTE_MEASURED_VALUE)
    if isinstance(raw, (int, float)):
        return float(raw) / 100.0
    return None

async def read_temperature_c(node_id: int) -> Optional[float]:
    resp = await get_node(node_id)
    return _find_temp_measuredvalue(resp)

async def read_humidity_rh(node_id: int) -> Optional[float]:
    resp = await get_node(node_id)
    return _find_humidity_measuredvalue(resp)

