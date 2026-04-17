export default function EventTimeline({ events, archiveCount = 0 }) {
  return (
    <div className="panel">
      <h2>Event Timeline</h2>
      <div style={{ marginBottom: 10 }}>
        Archived runs: <strong>{archiveCount}</strong>
      </div>

      <div className="timeline">
        {events.map((ev, idx) => {
          const isError =
            ev.event_type?.includes("FAIL") ||
            ev.event_type?.includes("ERROR") ||
            ev.event_type === "WARN" ||
            ev.event_type === "SESSION_TIMEOUT";

          return (
            <div key={idx} className={`timeline-item ${isError ? "error" : ""}`}>
              <div className="timeline-meta">
                <span>{ev.timestamp}</span>
                <span>{ev.source}</span>
                <span>{ev.event_type}</span>
                {ev.data?.error_code && <span>[{ev.data.error_code}]</span>}
              </div>
              <div className="timeline-message">{ev.message}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}