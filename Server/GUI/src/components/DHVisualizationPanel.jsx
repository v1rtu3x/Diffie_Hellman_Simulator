import React from "react";

export default function DHVisualizationPanel({ session }) {
  if (!session) {
    return null;
  }

  const aPub = session.public_keys?.["ESP32-A"];
  const bPub = session.public_keys?.["ESP32-B"];
  const aSecret = session.results?.["ESP32-A"];
  const bSecret = session.results?.["ESP32-B"];

  const verificationOk =
    session.verification_status === "PASS" &&
    aSecret !== undefined &&
    bSecret !== undefined;

  const verificationFail = session.verification_status === "FAIL";

  return (
    <div style={{ marginBottom: 20, padding: 12, border: "1px solid #ccc", borderRadius: 8 }}>
      <h2>DH Visualization</h2>

      <div style={{ marginBottom: 10 }}>
        <strong>Session:</strong> {session.session_id}
      </div>
      <div style={{ marginBottom: 10 }}>
        <strong>Status:</strong> {session.status}
      </div>
      <div style={{ marginBottom: 10 }}>
        <strong>Step:</strong> {session.current_step}
      </div>

      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        <div>
          <h3>Parameters</h3>
          <div>p = {session.p}</div>
          <div>g = {session.g}</div>
        </div>

        <div>
          <h3>ESP32-A</h3>
          <div>Public key: {aPub ?? "-"}</div>
          <div>Shared secret: {aSecret ?? "-"}</div>
        </div>

        <div>
          <h3>ESP32-B</h3>
          <div>Public key: {bPub ?? "-"}</div>
          <div>Shared secret: {bSecret ?? "-"}</div>
        </div>
      </div>

      <div style={{ marginTop: 14 }}>
        <strong>Verification:</strong>{" "}
        {verificationOk && (
          <span style={{ color: "green", fontWeight: "bold" }}>PASS</span>
        )}
        {verificationFail && (
          <span style={{ color: "red", fontWeight: "bold" }}>FAIL</span>
        )}
        {!verificationOk && !verificationFail && (
          <span style={{ color: "#555" }}>PENDING</span>
        )}
      </div>

      {verificationFail && (
        <div style={{ marginTop: 8, color: "#b91c1c", fontWeight: "bold" }}>
          Verification mismatch detected
        </div>
      )}
    </div>
  );
}