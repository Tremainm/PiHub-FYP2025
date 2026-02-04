# matterd/app.py
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import matter.native
from matter.ChipStack import ChipStack
from matter.storage import PersistentStorageJSON
from matter.CertificateAuthority import CertificateAuthorityManager

# ---------- Config ----------
CHIP_ROOT = Path("/home/pihub/connectedhomeip")
PAA_DIR = CHIP_ROOT / "credentials" / "development" / "paa-root-certs"

STORAGE_DIR = Path("/home/pihub/.pihub/matterd")
STORAGE_FILE = STORAGE_DIR / "controller-storage.json"

# If you need BLE commissioning, set to 0 (hci0). If not, you can keep 999.
BLE_ADAPTER_ID = 0

# Your controller identity on the fabric (keep stable)
CONTROLLER_NODE_ID = 112233
VENDOR_ID = 0xFFF1
FABRIC_ID = 1

app = FastAPI()


class CommissionBleRequest(BaseModel):
    discriminator: int
    setup_pin_code: int
    node_id: int
    ssid: str | None = None
    passcode: str | None = None
    is_short_discriminator: bool = True



@app.on_event("startup")
async def startup():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # Make sure relative PAA path works even if CHIP insists on it
    # (Alternative: run with WorkingDirectory set to CHIP_ROOT)
    # We'll just ensure the daemon's cwd is CHIP_ROOT.
    os.chdir(str(CHIP_ROOT))

    # Init native stack
    matter.native.Init(BLE_ADAPTER_ID)

    storage = PersistentStorageJSON(str(STORAGE_FILE))
    chip_stack = ChipStack(storage, enableServerInteractions=True)

    cam = CertificateAuthorityManager(chip_stack, chip_stack.GetStorageManager())
    cam.LoadAuthoritiesFromStorage()

    ca_list = (
        getattr(cam, "activeCaList", None)
        or getattr(cam, "caList", None)
        or getattr(cam, "_activeCaList", None)
        or []
    )
    ca = ca_list[0] if ca_list else cam.NewCertificateAuthority()

    admin_list = getattr(ca, "adminList", []) or []
    fabric_admin = admin_list[0] if admin_list else ca.NewFabricAdmin(vendorId=VENDOR_ID, fabricId=FABRIC_ID)

    devCtrl = fabric_admin.NewController(nodeId=CONTROLLER_NODE_ID)

    app.state.chip_stack = chip_stack
    app.state.cam = cam
    app.state.fabric_admin = fabric_admin
    app.state.devCtrl = devCtrl


@app.on_event("shutdown")
async def shutdown():
    # keep defensive shutdown
    try:
        getattr(app.state, "devCtrl", None) and app.state.devCtrl.Shutdown()
    except Exception:
        pass
    try:
        getattr(app.state, "chip_stack", None) and app.state.chip_stack.Shutdown()
    except Exception:
        pass


@app.get("/health")
def health():
    return {"ok": True}

@app.post("/commission/ble")
async def commission_ble(req: CommissionBleRequest):
    """
    BLE commissioning: connects over BLE and commissions to the fabric,
    assigning the device NodeId = req.node_id.
    Sets Wi-Fi Credentials before BLE commissioing
    """
    devCtrl = app.state.devCtrl
    try:
        if req.ssid is not None and req.passcode is not None:
            devCtrl.SetWiFiCredentials(req.ssid, req.passcode)

        await devCtrl.ConnectBLE(
            req.discriminator,
            req.setup_pin_code,
            req.node_id,
            isShortDiscriminator=req.is_short_discriminator,
        )
        return {"ok": True, "SSID": req.SSID, "Passcode": req.Passcode, "node_id": req.node_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @app.post("/commission/wifi-creds")
# async def commission_wifi_creds(req: WifiCredentials):
#     """
#     Set Wi-Fi credentials before BLE commissioning
#     """
#     devCtrl = app.state.devCtrl
#     try:
#         devCtrl.SetWiFiCredentials(
#             req.SSID,
#             req.Passcode
#         )
#         return {"ok": True, "SSID": req.SSID, "Passcode": req.Passcode}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/commission/ble")
# async def commission_ble(req: CommissionRequest):
#     """
#     BLE commissioning: connects over BLE and commissions to the fabric,
#     assigning the device NodeId = req.node_id.
#     """
#     devCtrl = app.state.devCtrl
#     try:
#         await devCtrl.ConnectBLE(
#             req.discriminator,
#             req.setup_pin_code,
#             req.node_id,
#             isShortDiscriminator=req.is_short_discriminator,
#         )
#         return {"ok": True, "node_id": req.node_id}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.get("/device/{node_id}/temperature_c")
async def read_temperature_c(node_id: int, endpoint: int = 1):
    """
    Example read. Adjust cluster/attribute IDs to match your sensor.
    For Matter TemperatureMeasurement cluster:
      cluster = 0x0402
      attribute MeasuredValue = 0x0000 (in 0.01°C units)
    """
    devCtrl = app.state.devCtrl

    try:
        # Many builds let you read attributes via ReadAttribute
        # The exact signature can vary — if yours differs, paste the error and I'll adapt.
        res = await devCtrl.ReadAttribute(node_id, [(endpoint, 0x0402, 0x0000)])
        # Typical structure is nested; you may need to inspect res once.
        raw = res[endpoint][0x0402][0x0000]
        temp_c = raw / 100.0
        return {"node_id": node_id, "temperature_c": temp_c}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
