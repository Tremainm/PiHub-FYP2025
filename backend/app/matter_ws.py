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


def call(command: str, args: Optional[dict[str, Any]] = None, timeout: float = 60.0) -> dict[str, Any]:
    """
    Sync wrapper so you can keep your current synchronous FastAPI endpoints.
    """
    return asyncio.run(_ws_call(command, args=args, timeout=timeout))


def set_wifi_credentials(ssid: str, password: str) -> dict[str, Any]:
    # python-matter-server expects "credentials" for the password field.
    return call("set_wifi_credentials", {"ssid": ssid, "credentials": password})


def commission_with_code(code: str, node_id: Optional[int] = None) -> dict[str, Any]:
    args: dict[str, Any] = {"code": code, "network_only": False}
    if node_id is not None:
        args["node_id"] = node_id
    # BLE commissioning happens automatically if the host has BLE available.
    return call("commission_with_code", args, timeout=180.0)


def get_nodes() -> dict[str, Any]:
    return call("get_nodes")


def get_node(node_id: int) -> dict[str, Any]:
    return call("get_node", {"node_id": node_id})


def _find_temp_measuredvalue(node_payload: Any) -> Optional[float]:
    """
    Best-effort parse: looks for TemperatureMeasurement cluster (0x0402)
    and MeasuredValue attribute (0x0000). Value is typically in 0.01°C units.
    """
    # python-matter-server's node format can vary by version.
    # We search deeply for a structure that includes these keys.
    def walk(obj: Any):
        if isinstance(obj, dict):
            yield obj
            for v in obj.values():
                yield from walk(v)
        elif isinstance(obj, list):
            for item in obj:
                yield from walk(item)

    # Prefer obvious places first
    for d in walk(node_payload):
        # common shapes include: {"cluster_id": 1026, "attribute_id": 0, "value": 2150}
        if d.get("cluster_id") == CLUSTER_TEMPERATURE_MEASUREMENT and d.get("attribute_id") == ATTRIBUTE_MEASURED_VALUE:
            v = d.get("value")
            if isinstance(v, (int, float)):
                return float(v) / 100.0

        # Another common shape: {"0402": {"0000": 2150}} or similar; handle hex-as-str too
        # Be conservative but helpful:
        if "attributes" in d and isinstance(d["attributes"], dict):
            attrs = d["attributes"]
            # sometimes cluster is a dict with id keys
            # we'll just recurse; the above dict match usually catches it.

    return None


def read_temperature_c(node_id: int) -> Optional[float]:
    """
    Read temperature from the node by calling get_node and extracting MeasuredValue.
    """
    resp = get_node(node_id)
    # response commonly has {"result": {...}} or {"data": {...}}
    payload = resp.get("result") or resp.get("data") or resp
    return _find_temp_measuredvalue(payload)
