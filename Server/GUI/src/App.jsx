import { useEffect, useState } from "react";
import { createSocket } from "./api";
import DeviceStatusPanel from "./components/DeviceStatusPanel";
import EventTimeline from "./components/EventTimeline";
import ControlPanel from "./components/ControlPanel";
import DHVisualizationPanel from "./components/DHVisualizationPanel";
import "./App.css";

export default function App() {
  const [devices, setDevices] = useState([]);
  const [session, setSession] = useState({
    session_id: "-",
    p: 23,
    g: 5,
    status: "IDLE",
    public_keys: {},
    results: {},
    devices_ready: [],
    verification_status: "PENDING",
    current_step: "IDLE",
    ready_to_start: false,
    exchange_complete: false,
    archive_count: 0,
    failure_reason: null,
  });
  const [events, setEvents] = useState([]);
  const [revealSecrets, setRevealSecrets] = useState(true);
  const [socketStatus, setSocketStatus] = useState("Connecting");

  useEffect(() => {
    const ws = createSocket((msg) => {
      if (msg.type === "snapshot") {
        setDevices(msg.payload.devices || []);
        setSession(msg.payload.session || {});
        setEvents(msg.payload.events || []);
      } else if (msg.type === "event") {
        setEvents((prev) => [...prev.slice(-99), msg.payload]);
      }
    });

    ws.onopen = () => {
      setSocketStatus("Connected");
    };

    ws.onclose = () => {
      setSocketStatus("Disconnected");
    };

    ws.onerror = (err) => {
      setSocketStatus("Error");
      console.error("WebSocket error", err);
    };

    return () => ws.close();
  }, []);

  const verificationBadgeClass =
    session.verification_status === "PASS"
      ? "success"
      : session.verification_status === "FAIL"
      ? "fail"
      : "pending";

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Diffie-Hellman Simulator</h1>
        <p>Live device status, session control, and event timeline</p>
      </header>

      <section className="section">
        <div className="panel">
          <h2>Demo Readiness</h2>
          <div>
            <strong>GUI ↔ Backend:</strong>{" "}
            <span className={`verify-badge ${socketStatus === "Connected" ? "success" : socketStatus === "Error" ? "fail" : "pending"}`}>
              {socketStatus}
            </span>
          </div>
          <div style={{ marginTop: 8 }}>
            <strong>Ready to start:</strong>{" "}
            <span className={`verify-badge ${session.ready_to_start ? "success" : "pending"}`}>
              {session.ready_to_start ? "YES" : "NO"}
            </span>
          </div>
          <div style={{ marginTop: 8 }}>
            <strong>Exchange complete:</strong>{" "}
            <span className={`verify-badge ${session.exchange_complete ? "success" : "pending"}`}>
              {session.exchange_complete ? "YES" : "NO"}
            </span>
          </div>
          <div style={{ marginTop: 8 }}>
            <strong>Current session:</strong> {session.session_id}
          </div>
          <div style={{ marginTop: 12 }}>
            <strong>Operator workflow:</strong>
            <ol style={{ marginTop: 8 }}>
              <li>Connect both ESP32 devices</li>
              <li>Wait for both heartbeat indicators to become healthy</li>
              <li>Set p and g</li>
              <li>Start exchange</li>
              <li>Verify shared secret result</li>
              <li>Reset and repeat</li>
            </ol>
          </div>
          <div style={{ marginTop: 12, color: "#92400e" }}>
            If a device goes offline, check USB power, hotspot, backend process, then wait for heartbeat recovery or press Reset.
          </div>
        </div>
      </section>

      <section className="section">
        <ControlPanel readyToStart={session.ready_to_start} />
      </section>

      <section className="section">
        <div className="panel">
          <h2>Visibility Controls</h2>
          <label>
            <input
              type="checkbox"
              checked={revealSecrets}
              onChange={(e) => setRevealSecrets(e.target.checked)}
            />
            Reveal secrets for demo mode
          </label>
        </div>
      </section>

      <section className="section">
        <DeviceStatusPanel devices={devices} session={session} />
      </section>

      <section className="section">
        <DHVisualizationPanel
          session={session}
          events={events}
          revealSecrets={revealSecrets}
        />
      </section>

      <section className="session-panel section">
        <h2>Session Status</h2>
        <div className="session-grid">
          <div><strong>Session ID:</strong> {session.session_id}</div>
          <div><strong>Status:</strong> {session.status}</div>
          <div><strong>Current step:</strong> {session.current_step || "-"}</div>
          <div>
            <strong>Verification:</strong>{" "}
            <span className={`verify-badge ${verificationBadgeClass}`}>
              {session.verification_status || "PENDING"}
            </span>
          </div>
          <div><strong>p:</strong> {session.p ?? "-"}</div>
          <div><strong>g:</strong> {session.g ?? "-"}</div>
          <div><strong>Ready devices:</strong> {session.devices_ready?.join(", ") || "-"}</div>
          <div><strong>Archived runs:</strong> {session.archive_count ?? 0}</div>
        </div>

        {session.failure_reason && (
          <div style={{ marginTop: 12 }}>
            <span className="verify-badge fail">
              Session failure: {session.failure_reason}
            </span>
          </div>
        )}

        <div className="session-json-grid" style={{ marginTop: 16 }}>
          <div>
            <h3>Public Keys</h3>
            <pre>{JSON.stringify(session.public_keys || {}, null, 2)}</pre>
          </div>
          <div>
            <h3>Results</h3>
            <pre>{JSON.stringify(session.results || {}, null, 2)}</pre>
          </div>
        </div>
      </section>

      <section className="section">
        <EventTimeline events={events} archiveCount={session.archive_count || 0} />
      </section>
    </div>
  );
}