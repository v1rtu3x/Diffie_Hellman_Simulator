import { useState } from "react";
import { startSession, resetSession } from "../api";

export default function ControlPanel() {
  const [p, setP] = useState(23);
  const [g, setG] = useState(5);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  async function handleStart() {
    setBusy(true);
    setStatus("Starting session...");
    try {
      await startSession(Number(p), Number(g));
      setStatus("Start request sent.");
    } catch (err) {
      console.error(err);
      setStatus(`Start failed: ${err.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleReset() {
    setBusy(true);
    setStatus("Resetting session...");
    try {
      await resetSession();
      setStatus("Reset request sent.");
    } catch (err) {
      console.error(err);
      setStatus(`Reset failed: ${err.message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <h2>Control Panel</h2>

      <div className="control-row">
        <label>
          p
          <input value={p} onChange={(e) => setP(e.target.value)} />
        </label>

        <label>
          g
          <input value={g} onChange={(e) => setG(e.target.value)} />
        </label>
      </div>

      <div className="control-actions">
        <button onClick={handleStart} disabled={busy}>Start Session</button>
        <button onClick={handleReset} disabled={busy} className="secondary">Reset Session</button>
      </div>

      {status && <div style={{ marginTop: 12 }}>{status}</div>}
    </div>
  );
}