import { useState, useEffect } from "react";
import { getDevices, registerDevice, unregisterDevice } from "../api/devices";
import { getMatterNodes, removeNode, setWifiCredentials, commissionDevice } from "../api/matter";

export default function Settings() {
  // ── Wi-Fi credentials ──────────────────────────────────────────────────────
  const [ssid,     setSsid]     = useState("");
  const [password, setPassword] = useState("");
  const [wifiMsg,  setWifiMsg]  = useState(null);

  // ── Commissioning ──────────────────────────────────────────────────────────
  const [pairingCode,    setPairingCode]    = useState("");
  const [newNodeName,    setNewNodeName]    = useState("");
  const [networkOnly,    setNetworkOnly]    = useState(false);
  const [commissionMsg,  setCommissionMsg]  = useState(null);
  const [commissioning,  setCommissioning]  = useState(false);

  // ── Device management ──────────────────────────────────────────────────────
  const [devices,    setDevices]    = useState([]);
  const [removeMsg,  setRemoveMsg]  = useState(null);

  useEffect(() => { loadDevices(); }, []);

  function loadDevices() {
    getDevices().then(setDevices).catch(console.error);
  }

  // ── Handlers ───────────────────────────────────────────────────────────────

  async function handleSetWifi(e) {
    e.preventDefault();
    setWifiMsg({ type: "info", text: "Setting credentials…" });
    try {
      await setWifiCredentials(ssid, password);
      setWifiMsg({ type: "success", text: "Wi-Fi credentials saved to matter-server." });
      setSsid(""); setPassword("");
    } catch (err) {
      setWifiMsg({ type: "error", text: err.message });
    }
  }

  async function handleCommission(e) {
    e.preventDefault();
    if (!pairingCode.trim()) return;
    setCommissioning(true);
    setCommissionMsg({ type: "info", text: "Commissioning… this may take up to 2 minutes." });
    try {
      const result = await commissionDevice(pairingCode.trim(), null, networkOnly);
      const node_id = result?.result?.node_id ?? result?.node_id;
      setCommissionMsg({ type: "success", text: `Device commissioned as node ${node_id}.` });

      // Register a name if provided
      if (node_id && newNodeName.trim()) {
        await registerDevice(node_id, newNodeName.trim());
        loadDevices();
      }

      setPairingCode(""); setNewNodeName("");
    } catch (err) {
      setCommissionMsg({ type: "error", text: err.message });
    } finally {
      setCommissioning(false);
    }
  }

  async function handleRemove(device) {
    if (!window.confirm(`Remove "${device.name}" (node ${device.node_id}) from the fabric? The device will need a factory reset to re-commission.`)) return;
    setRemoveMsg({ type: "info", text: `Removing ${device.name}…` });
    try {
      await removeNode(device.node_id);
      await unregisterDevice(device.node_id);
      loadDevices();
      setRemoveMsg({ type: "success", text: `${device.name} removed.` });
    } catch (err) {
      setRemoveMsg({ type: "error", text: err.message });
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Network, commissioning, and device management</p>
      </div>

      {/* Wi-Fi credentials */}
      <div className="settings-section">
        <div className="settings-section-title">Wi-Fi Credentials</div>
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16 }}>
          Set these before commissioning a Wi-Fi Matter device. Credentials are
          stored in matter-server for the duration of commissioning only.
        </p>
        <form onSubmit={handleSetWifi}>
          <div className="settings-row">
            <input
              className="form-input"
              placeholder="SSID"
              value={ssid}
              onChange={(e) => setSsid(e.target.value)}
              required
            />
            <input
              className="form-input"
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button className="btn btn-primary" type="submit">Save Credentials</button>
          </div>
        </form>
        {wifiMsg && <div className={`status-msg ${wifiMsg.type}`}>{wifiMsg.text}</div>}
      </div>

      {/* Commission */}
      <div className="settings-section">
        <div className="settings-section-title">Commission a New Device</div>
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16 }}>
          Enter the QR code string (MT:…) or 11-digit manual pairing code from the device.
          For Wi-Fi devices, save Wi-Fi credentials above first.
        </p>
        <form onSubmit={handleCommission}>
          <div className="settings-row">
            <input
              className="form-input"
              placeholder="Pairing code (MT:… or 11 digits)"
              value={pairingCode}
              onChange={(e) => setPairingCode(e.target.value)}
              required
            />
            <input
              className="form-input"
              placeholder="Device name (e.g. Living Room Sensor)"
              value={newNodeName}
              onChange={(e) => setNewNodeName(e.target.value)}
            />
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, color: "var(--text-dim)", minHeight: "var(--touch)" }}>
              <input
                type="checkbox"
                checked={networkOnly}
                onChange={(e) => setNetworkOnly(e.target.checked)}
                style={{ width: 18, height: 18 }}
              />
              Skip Bluetooth (network/IP only)
            </label>
            <button className="btn btn-primary" type="submit" disabled={commissioning}>
              {commissioning ? "Commissioning…" : "Commission Device"}
            </button>
          </div>
        </form>
        {commissionMsg && <div className={`status-msg ${commissionMsg.type}`}>{commissionMsg.text}</div>}
      </div>

      {/* Device list + removal */}
      <div className="settings-section">
        <div className="settings-section-title">Registered Devices</div>

        {removeMsg && <div className={`status-msg ${removeMsg.type}`} style={{ marginBottom: 14 }}>{removeMsg.text}</div>}

        {devices.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: 14 }}>No devices registered yet.</p>
        ) : (
          <div className="node-list">
            {devices.map((d) => (
              <div className="node-row" key={d.node_id}>
                <div className="node-info">
                  <div className="node-name">{d.name}</div>
                  <div className="node-id">node_id: {d.node_id}</div>
                </div>
                <button className="btn btn-danger" onClick={() => handleRemove(d)}>
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}

        <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 16, lineHeight: 1.6 }}>
          Note: Removing a device decommissions it from the Matter fabric and removes it
          from the name registry. The device will need a factory reset before it can be
          re-commissioned. If you are changing Wi-Fi networks, you may also need to clear
          the <code style={{ fontFamily: "var(--font-mono)" }}>/data</code> directory inside the
          matter-server container and re-commission from scratch.
        </p>
      </div>
    </div>
  );
}