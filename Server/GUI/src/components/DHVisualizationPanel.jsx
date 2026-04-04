function maskValue(value, hidden) {
  if (value === undefined || value === null) return "-";
  return hidden ? "••••" : String(value);
}

const STEP_ORDER = [
  "PARAMS_DISTRIBUTED",
  "PRIVATE_KEYS_GENERATED",
  "PUBLIC_KEYS_COMPUTED",
  "PUBLIC_KEYS_EXCHANGED",
  "SHARED_SECRET_COMPUTED",
  "VERIFICATION_COMPLETE",
];

const STEP_LABELS = {
  PARAMS_DISTRIBUTED: "Params distributed",
  PRIVATE_KEYS_GENERATED: "Private keys generated",
  PUBLIC_KEYS_COMPUTED: "Public keys computed",
  PUBLIC_KEYS_EXCHANGED: "Public keys exchanged",
  SHARED_SECRET_COMPUTED: "Shared secret computed",
  VERIFICATION_COMPLETE: "Verification complete",
};

export default function DHVisualizationPanel({ session, revealSecrets }) {
  const publicA = session.public_keys?.["ESP32-A"];
  const publicB = session.public_keys?.["ESP32-B"];
  const resultA = session.results?.["ESP32-A"];
  const resultB = session.results?.["ESP32-B"];

  const currentStep = session.current_step || "IDLE";
  const currentIndex = STEP_ORDER.indexOf(currentStep);

  const verification =
    session.verification_status ||
    (session.status === "VERIFIED_OK"
      ? "PASS"
      : session.status === "VERIFIED_FAIL"
      ? "FAIL"
      : "PENDING");

  const relayActive = currentStep === "PUBLIC_KEYS_EXCHANGED" || session.status === "RELAYING_PUBLIC_KEYS";

  return (
    <div className="panel">
      <h2>Diffie-Hellman Visualization</h2>

      <div className="viz-grid">
        <div className="viz-card">
          <h3>Parameters</h3>
          <div><strong>p:</strong> {session.p}</div>
          <div><strong>g:</strong> {session.g}</div>
        </div>

        <div className="viz-card">
          <h3>ESP32-A</h3>
          <div><strong>Public Key:</strong> {maskValue(publicA, false)}</div>
          <div><strong>Shared Secret:</strong> {maskValue(resultA, !revealSecrets)}</div>
        </div>

        <div className="viz-card">
          <h3>ESP32-B</h3>
          <div><strong>Public Key:</strong> {maskValue(publicB, false)}</div>
          <div><strong>Shared Secret:</strong> {maskValue(resultB, !revealSecrets)}</div>
        </div>
      </div>

      <div className="relay-lane">
        <div className="relay-endpoint">ESP32-A</div>
        <div className={`relay-track ${relayActive ? "active" : ""}`}></div>
        <div className="relay-endpoint">ESP32-B</div>
      </div>

      <div className="step-flow">
        <h3>Exchange Steps</h3>
        <div className="step-list">
          {STEP_ORDER.map((step, idx) => {
            const isActive = idx === currentIndex;
            const isDone = currentIndex > idx;

            return (
              <div
                key={step}
                className={`step-node ${isActive ? "active" : ""} ${isDone ? "done" : ""}`}
              >
                {STEP_LABELS[step]}
              </div>
            );
          })}
        </div>
      </div>

      <div
        className={`verify-badge ${
          verification === "PASS"
            ? "success"
            : verification === "FAIL"
            ? "fail"
            : "pending"
        }`}
      >
        Verification: {verification}
      </div>
    </div>
  );
}