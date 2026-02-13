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
    Sync wrapper so I can keep my current synchronous FastAPI endpoints.
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

def read_temperature_c(node_id: int) -> Optional[float]:
    resp = get_node(node_id)
    return _find_temp_measuredvalue(resp)

# def read_humidity_rh(node_id: int) -> Optional[float]:
#     resp = get_node(node_id)
#     attrs = resp.get("result", {}).get("attributes", {})
#     raw = attrs.get("2/1029/0")
#     if isinstance(raw, (int, float)):
#         return float(raw) / 100.0
#     return None

