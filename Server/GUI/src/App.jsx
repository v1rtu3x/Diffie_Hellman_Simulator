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
  });
  const [events, setEvents] = useState([]);
  const [revealSecrets, setRevealSecrets] = useState(true);

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

    return () => ws.close();
  }, []);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Diffie-Hellman Simulator</h1>
        <p>Live device status, session control, and event timeline</p>
      </header>

      <section className="section">
        <ControlPanel />
      </section>

      <section className="section">
        <div className="panel">
          <h2>Visibility Controls</h2>
          <label>
            <input
              type="checkbox"
              checked={revealSecrets}
              onChange={(e) => setRevealSecrets(e.target.checked)}
            />{" "}
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
          revealSecrets={revealSecrets}
        />
      </section>

      <section className="session-panel section">
        <h2>Session Status</h2>
        <div className="session-grid">
          <div><strong>Session ID:</strong> {session.session_id}</div>
          <div><strong>Status:</strong> {session.status}</div>
          <div><strong>Current step:</strong> {session.current_step || "-"}</div>
          <div><strong>Verification:</strong> {session.verification_status || "PENDING"}</div>
          <div><strong>p:</strong> {session.p}</div>
          <div><strong>g:</strong> {session.g}</div>
          <div><strong>Ready devices:</strong> {session.devices_ready?.join(", ") || "-"}</div>
        </div>

        <div className="session-json-grid">
          <div>
            <h3>Public Keys</h3>
            <pre>{JSON.stringify(session.public_keys, null, 2)}</pre>
          </div>
          <div>
            <h3>Results</h3>
            <pre>{JSON.stringify(session.results, null, 2)}</pre>
          </div>
        </div>
      </section>

      <section className="section">
        <EventTimeline events={events} />
      </section>
    </div>
  );
}