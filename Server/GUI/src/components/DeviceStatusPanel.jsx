function DeviceCard({ title, device, fallbackSessionId }) {
  const connected = Boolean(device);
  const health = device?.heartbeat_health || "offline";
  const offline = !connected || health === "offline";

  return (
    <div className="panel device-card">
      <h2>{title}</h2>

      <div className="device-row">
        <span className={`badge ${connected && !offline ? "ok" : "off"}`}>
          {connected && !offline ? "Connected" : "Offline"}
        </span>
        <span style={{ marginLeft: 8 }}>
          Heartbeat: <strong>{health}</strong>
        </span>
      </div>

      {device ? (
        <div className="device-details">
          <div><strong>Address:</strong> {device.addr}</div>
          <div><strong>Firmware:</strong> {device.firmware_version || "-"}</div>
          <div><strong>State:</strong> {device.state || "-"}</div>
          <div><strong>Session:</strong> {device.session_id || fallbackSessionId || "-"}</div>
          <div><strong>Last seen:</strong> {device.last_seen}</div>
        </div>
      ) : (
        <div className="device-details">
          <div><strong>State:</strong> OFFLINE</div>
        </div>
      )}

      {offline && (
        <div style={{ marginTop: 12, color: "#991b1b", fontWeight: 700 }}>
          No recent heartbeat. Check power, hotspot, or backend.
        </div>
      )}
    </div>
  );
}

export default function DeviceStatusPanel({ devices, session }) {
  const deviceA = devices.find((d) => d.device_id === "ESP32-A");
  const deviceB = devices.find((d) => d.device_id === "ESP32-B");

  return (
    <div className="device-grid">
      <DeviceCard title="ESP32-A" device={deviceA} fallbackSessionId={session.session_id} />
      <DeviceCard title="ESP32-B" device={deviceB} fallbackSessionId={session.session_id} />
    </div>
  );
}