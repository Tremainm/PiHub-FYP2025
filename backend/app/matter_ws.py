"""
matter_ws.py — Single-connection Matter WebSocket client.

Architecture
------------
One persistent WebSocket connection handles everything:

  ┌──────────────────────────────────────────────────────┐
  │              _background_listener() loop             │
  │                                                      │
  │  start_listening dump  →  populate _attribute_cache  │
  │  attribute_updated     →  update cache               │
  │  node_updated          →  update cache               │
  │  node_added            →  update cache               │
  │  node_removed          →  evict from cache           │
  │  msg_id in _pending    →  resolve Future for caller  │
  └──────────────────────────────────────────────────────┘

Commands (turn_on, commission, remove_node, etc.) use _ws_call(),
which sends over the SAME connection and registers an asyncio.Future
in _pending. The listener loop resolves that Future when the matching
response arrives — no second connection is ever opened, so no
subscription events are stolen or discarded.

Sensor data is read exclusively from _attribute_cache, populated by
the live subscription stream.
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Optional

import websockets

logger = logging.getLogger(__name__)

# ── Connection ────────────────────────────────────────────────────────────────

MATTER_WS_URL = os.getenv("MATTER_WS_URL", "ws://127.0.0.1:5580/ws")

# The single shared WebSocket object. None while disconnected/reconnecting.
_ws: Optional[Any] = None

# Pending one-shot calls: message_id → asyncio.Future.
# The listener loop resolves these when the matching response arrives.
_pending: dict[str, asyncio.Future] = {}

# ── Attribute cache ───────────────────────────────────────────────────────────

# Keyed by (node_id, attribute_path), e.g. (1, "1/1026/0") → 1820
_attribute_cache: dict[tuple[int, str], Any] = {}

# ── Subscriber callbacks ──────────────────────────────────────────────────────

# (node_id, attribute_path) → list of async callables
# Signature: async def cb(node_id: int, attr_path: str, value: Any) -> None
_subscribers: dict[tuple[int, str], list] = {}

# ── Matter cluster / attribute constants ──────────────────────────────────────

CLUSTER_ON_OFF        = 0x0006
CLUSTER_LEVEL_CONTROL = 0x0008
CLUSTER_COLOR_CONTROL = 0x0300
CLUSTER_TEMPERATURE   = 0x0402  # Temperature Measurement
CLUSTER_HUMIDITY      = 0x0405  # Relative Humidity Measurement

ATTR_MEASURED_VALUE   = 0x0000  # Used by both temp and humidity clusters
ATTR_ON_OFF           = 0x0000  # OnOff cluster — current on/off state
ATTR_CURRENT_LEVEL    = 0x0000  # LevelControl — current brightness level
ATTR_COLOR_X          = 0x0003  # ColorControl — CIE x coordinate
ATTR_COLOR_Y          = 0x0004  # ColorControl — CIE y coordinate

# ── Background listener ───────────────────────────────────────────────────────

async def _background_listener() -> None:
    """
    Long-lived task that maintains the single shared WebSocket connection to
    python-matter-server.

    On connect, sends `start_listening`. The server responds with a full dump
    of all known nodes (used to warm up _attribute_cache immediately), then
    streams live attribute_updated and node events indefinitely.

    Two categories of incoming messages are handled:

    1. Command responses — any message whose message_id matches an entry in
       _pending. The corresponding asyncio.Future is resolved, waking up
       whatever coroutine is awaiting _ws_call().

    2. Events — attribute_updated, node_updated, node_added, node_removed.
       These update _attribute_cache so /live endpoints always return fresh data.

    On disconnect, pending Futures are cancelled immediately (ConnectionError)
    so callers don't hang until timeout. Reconnect is attempted after 5 seconds.
    """
    global _ws

    while True:
        try:
            async with websockets.connect(
                MATTER_WS_URL,
                ping_interval=20,
                ping_timeout=20,
            ) as ws:
                _ws = ws
                logger.info("Connected to matter-server — sending start_listening")

                listen_id = uuid.uuid4().hex
                await ws.send(json.dumps({
                    "message_id": listen_id,
                    "command": "start_listening",
                }))

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning("Received non-JSON message, skipping")
                        continue

                    msg_id = msg.get("message_id")

                    # ── 1. Resolve a pending _ws_call() Future ────────────
                    # Any message whose ID is in _pending is a command
                    # response. Resolve the Future so the awaiting coroutine
                    # continues with the result.
                    if msg_id and msg_id != listen_id and msg_id in _pending:
                        future = _pending.pop(msg_id)
                        if not future.done():
                            future.set_result(msg)
                        continue

                    # ── 2. Initial start_listening node dump ──────────────
                    # result is a list of MatterNode dicts. Cache all
                    # attributes immediately so /live endpoints have data
                    # from the first request after startup.
                    if msg_id == listen_id:
                        nodes = msg.get("result", [])
                        if isinstance(nodes, list):
                            for node in nodes:
                                _cache_node(node)
                        logger.info(
                            "Cache warm-up complete — %d entries", len(_attribute_cache)
                        )
                        continue

                    # ── 3. Live events ────────────────────────────────────
                    event = msg.get("event")

                    if event == "attribute_updated":
                        # data is a list: [node_id, attribute_path, value]
                        data = msg.get("data")
                        if not isinstance(data, list) or len(data) != 3:
                            continue
                        node_id, attr_path, value = data

                        key = (node_id, attr_path)
                        _attribute_cache[key] = value
                        logger.debug(
                            "attribute_updated node=%s path=%s value=%s",
                            node_id, attr_path, value,
                        )
                        for cb in _subscribers.get(key, []):
                            try:
                                await cb(node_id, attr_path, value)
                            except Exception as exc:
                                logger.error("Subscriber callback error: %s", exc)

                    elif event in ("node_updated", "node_added"):
                        # node_updated: full attribute refresh, e.g. after reconnect.
                        # node_added:   newly commissioned node has been interviewed.
                        # Both carry a full MatterNode dict in data.
                        data = msg.get("data", {})
                        if isinstance(data, dict):
                            _cache_node(data)

                    elif event == "node_removed":
                        # A node was decommissioned — evict its cache entries.
                        data = msg.get("data", {})
                        if isinstance(data, dict):
                            node_id = data.get("node_id")
                            if node_id is not None:
                                _evict_node(node_id)

        except (websockets.ConnectionClosed, OSError) as exc:
            logger.warning("matter-server disconnected: %s — reconnecting in 5s", exc)
        finally:
            _ws = None
            # Cancel pending Futures so callers get an immediate error
            # instead of waiting for a timeout that will never fire.
            for fut in _pending.values():
                if not fut.done():
                    fut.set_exception(
                        ConnectionError("WebSocket disconnected — retry after reconnect")
                    )
            _pending.clear()
            await asyncio.sleep(5)


def _cache_node(node: dict) -> None:
    """
    Write all attributes from a MatterNode dict into _attribute_cache.
    Attribute keys are "endpoint/cluster/attribute" strings, e.g. "1/1026/0".
    """
    node_id    = node.get("node_id")
    attributes = node.get("attributes", {})
    if node_id is not None and isinstance(attributes, dict):
        for path, value in attributes.items():
            _attribute_cache[(node_id, path)] = value


def _evict_node(node_id: int) -> None:
    """Remove all cached attributes for a decommissioned node."""
    for key in [k for k in _attribute_cache if k[0] == node_id]:
        del _attribute_cache[key]


# ── Public startup ────────────────────────────────────────────────────────────

def start_background_listener() -> None:
    """
    Call once at app startup inside a FastAPI lifespan handler.
    Creates an asyncio task that runs _background_listener() concurrently
    with FastAPI's own event loop.
    """
    asyncio.ensure_future(_background_listener())


# ── Callback registration ────────────────────────────────────────────────────

def register_callback(node_id: int, attribute_path: str, callback) -> None:
    """
    Register an async callback to fire whenever a specific attribute updates.

    The callback is called by the background listener immediately after the
    cache is updated, so the cache is always fresh by the time your callback runs.

    Callback signature:
        async def cb(node_id: int, attr_path: str, value: Any) -> None

    Example — persist temperature changes for node 2:
        async def on_temp(node_id, path, value):
            await save_to_db(node_id, value / 100.0)

        register_callback(2, "1/1026/0", on_temp)
    """
    key = (node_id, attribute_path)
    _subscribers.setdefault(key, []).append(callback)


# ── Command transport ─────────────────────────────────────────────────────────

async def _ws_call(
    command: str,
    args: Optional[dict[str, Any]] = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """
    Send a command over the shared persistent connection and await its response.

    Registers an asyncio.Future in _pending keyed by a unique message_id,
    sends the JSON payload over _ws, then awaits the Future. The listener
    loop resolves the Future when the matching response arrives — no second
    connection is opened and no subscription events are discarded.

    Raises:
        ConnectionError — not yet connected (listener starting/reconnecting)
        TimeoutError    — server didn't respond within `timeout` seconds
    """
    if _ws is None:
        raise ConnectionError(
            "Not connected to matter-server yet. "
            "Is start_background_listener() running and the server reachable?"
        )

    message_id = uuid.uuid4().hex
    payload: dict[str, Any] = {"message_id": message_id, "command": command}
    if args:
        payload["args"] = args

    future: asyncio.Future = asyncio.get_event_loop().create_future()
    _pending[message_id] = future

    try:
        await _ws.send(json.dumps(payload))
        return await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        _pending.pop(message_id, None)
        raise TimeoutError(f"Command '{command}' timed out after {timeout}s")
    except Exception:
        _pending.pop(message_id, None)
        raise


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _find_cached(node_id: int, cluster_id: int, attribute_id: int = 0) -> Optional[Any]:
    """
    Search _attribute_cache for any endpoint on node_id that matches the given
    cluster and attribute. Returns the raw value or None.

    We search all endpoints rather than hardcoding endpoint 1 because different
    device types may place the same cluster on different endpoints.
    Attribute path format: "endpoint/cluster/attribute" e.g. "1/1026/0".
    """
    for (nid, path), value in _attribute_cache.items():
        if nid != node_id:
            continue
        parts = path.split("/")
        if len(parts) == 3:
            _, c, a = parts
            if int(c) == cluster_id and int(a) == attribute_id:
                return value
    return None


# ── Cache readers ─────────────────────────────────────────────────────────────

def get_cached_temperature(node_id: int) -> Optional[float]:
    """
    Latest temperature in °C from the subscription cache.
    Matter stores temperature as hundredths of a degree (e.g. 2150 = 21.50°C).
    Returns None if no reading has arrived yet.
    """
    raw = _find_cached(node_id, CLUSTER_TEMPERATURE, ATTR_MEASURED_VALUE)
    return float(raw) / 100.0 if isinstance(raw, (int, float)) else None


def get_cached_humidity(node_id: int) -> Optional[float]:
    """
    Latest relative humidity (%RH) from the subscription cache.
    Matter stores humidity as hundredths of a percent (e.g. 5940 = 59.40%RH).
    Returns None if no reading has arrived yet.
    """
    raw = _find_cached(node_id, CLUSTER_HUMIDITY, ATTR_MEASURED_VALUE)
    return float(raw) / 100.0 if isinstance(raw, (int, float)) else None


def get_cached_on_off(node_id: int) -> Optional[bool]:
    """Current on/off state from cache. None if not yet received."""
    raw = _find_cached(node_id, CLUSTER_ON_OFF, ATTR_ON_OFF)
    return bool(raw) if raw is not None else None


def get_cached_brightness(node_id: int) -> Optional[int]:
    """Current brightness level (0-254) from cache. None if not yet received."""
    raw = _find_cached(node_id, CLUSTER_LEVEL_CONTROL, ATTR_CURRENT_LEVEL)
    return int(raw) if isinstance(raw, (int, float)) else None


def get_cached_color_xy(node_id: int) -> Optional[dict[str, float]]:
    """
    Current CIE XY colour coordinates from cache as floats 0.0-1.0.
    Matter stores these as integers scaled by 65536.
    Returns None if not yet received.
    """
    x_raw = _find_cached(node_id, CLUSTER_COLOR_CONTROL, ATTR_COLOR_X)
    y_raw = _find_cached(node_id, CLUSTER_COLOR_CONTROL, ATTR_COLOR_Y)
    if x_raw is None or y_raw is None:
        return None
    return {"x": round(x_raw / 65536, 6), "y": round(y_raw / 65536, 6)}


def get_cached_sensor_data(node_id: int) -> dict[str, Optional[float]]:
    """Both sensor readings in one call."""
    return {
        "temperature_c": get_cached_temperature(node_id),
        "humidity_rh":   get_cached_humidity(node_id),
    }


def get_cached_light_state(node_id: int) -> dict[str, Any]:
    """Full light state (on/off, brightness, colour) in one call."""
    return {
        "on":         get_cached_on_off(node_id),
        "brightness": get_cached_brightness(node_id),
        "color_xy":   get_cached_color_xy(node_id),
    }


# ── Node management ───────────────────────────────────────────────────────────

async def get_nodes() -> dict[str, Any]:
    """Return all nodes currently in the Matter fabric."""
    return await _ws_call("get_nodes")


async def remove_node(node_id: int) -> dict[str, Any]:
    """
    Decommission a node from the fabric. The device will need a factory reset
    before it can be re-commissioned. Triggers a node_removed event which
    automatically evicts the node from _attribute_cache.
    """
    return await _ws_call("remove_node", {"node_id": node_id})


# ── Commissioning ─────────────────────────────────────────────────────────────

async def set_wifi_credentials(ssid: str, password: str) -> dict[str, Any]:
    """
    Pre-load Wi-Fi credentials into matter-server before commissioning a
    Wi-Fi device. Must be called before commission_with_code() for Wi-Fi devices.
    python-matter-server uses the field name "credentials" for the password.
    """
    return await _ws_call("set_wifi_credentials", {
        "ssid":        ssid,
        "credentials": password,
    })


async def commission_with_code(
    code: str,
    node_id: Optional[int] = None,
    network_only: bool = False,
) -> dict[str, Any]:
    """
    Commission a new Matter device into the fabric.

    Args:
        code:         QR code string (MT:...) or 11-digit manual pairing code.
        node_id:      Optional specific node_id to assign. Auto-assigned if None.
        network_only: Skip BLE and use mDNS/IP only. Use this if the host has
                      no Bluetooth or the device is already on the network.

    For Wi-Fi devices: call set_wifi_credentials() first.
    Commissioning can take 60-120 seconds; timeout is set to 180s.
    On success, matter-server emits node_added which populates the cache.
    """
    args: dict[str, Any] = {"code": code, "network_only": network_only}
    if node_id is not None:
        args["node_id"] = node_id
    return await _ws_call("commission_with_code", args, timeout=180.0)


# ── LED commands ──────────────────────────────────────────────────────────────

async def _send_command(
    node_id: int,
    endpoint_id: int,
    cluster_id: int,
    command_name: str,
    payload: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Send a Matter cluster command via python-matter-server's device_command API.

    Args:
        node_id:      The commissioned node's ID.
        endpoint_id:  Which endpoint hosts the cluster (1 for most lights).
        cluster_id:   Matter cluster ID (e.g. 0x0006 for OnOff).
        command_name: String name of the command (e.g. "On", "MoveToLevel").
        payload:      Command fields dict; use {} for commands with no arguments.
    """
    return await _ws_call("device_command", {
        "node_id":      node_id,
        "endpoint_id":  endpoint_id,
        "cluster_id":   cluster_id,
        "command_name": command_name,
        "payload":      payload or {},
    })


async def turn_on(node_id: int, endpoint_id: int = 1) -> dict[str, Any]:
    """Send OnOff:On. Sets the device to the ON state."""
    return await _send_command(node_id, endpoint_id, CLUSTER_ON_OFF, "On")


async def turn_off(node_id: int, endpoint_id: int = 1) -> dict[str, Any]:
    """Send OnOff:Off. Sets the device to the OFF state."""
    return await _send_command(node_id, endpoint_id, CLUSTER_ON_OFF, "Off")


async def toggle(node_id: int, endpoint_id: int = 1) -> dict[str, Any]:
    """
    Send OnOff:Toggle. Flips current state without needing to know it.
    Ideal for a single button press where you don't want to read state first.
    """
    return await _send_command(node_id, endpoint_id, CLUSTER_ON_OFF, "Toggle")


async def set_brightness(
    node_id: int,
    level: int,
    transition_time: int = 0,
    endpoint_id: int = 1,
) -> dict[str, Any]:
    """
    Set brightness via LevelControl:MoveToLevel.

    Args:
        level:           Target brightness 0-254 (0=minimum, 254=maximum).
                         Note: level 0 does NOT change the OnOff state. Use
                         turn_off() for a clean off so the bulb remembers its
                         last brightness level for the next turn_on().
        transition_time: Fade duration in tenths of a second (0 = immediate).
                         E.g. transition_time=10 fades over 1 second.

    optionsMask/optionsOverride=0 means execute regardless of current OnOff
    state, which is the standard best practice for this command.
    """
    return await _send_command(
        node_id, endpoint_id, CLUSTER_LEVEL_CONTROL, "MoveToLevel",
        {
            "level":           max(0, min(254, level)),
            "transitionTime":  transition_time,
            "optionsMask":     0,
            "optionsOverride": 0,
        },
    )


async def set_color_xy(
    node_id: int,
    x: float,
    y: float,
    transition_time: int = 0,
    endpoint_id: int = 1,
) -> dict[str, Any]:
    """
    Set colour via ColorControl:MoveToColor using CIE 1931 XY chromaticity.

    Args:
        x, y:            CIE XY coordinates as floats 0.0-1.0.
                         Matter stores these as integers scaled by 65536.
        transition_time: Fade in tenths of a second.

    Useful XY presets:
        Red:        x=0.700, y=0.299
        Green:      x=0.172, y=0.747
        Blue:       x=0.136, y=0.040
        Warm white: x=0.450, y=0.408
        Cool white: x=0.313, y=0.329
    """
    return await _send_command(
        node_id, endpoint_id, CLUSTER_COLOR_CONTROL, "MoveToColor",
        {
            "colorX":          int(x * 65536),
            "colorY":          int(y * 65536),
            "transitionTime":  transition_time,
            "optionsMask":     0,
            "optionsOverride": 0,
        },
    )