export default function EventTimeline({ events }) {
  return (
    <div className="panel">
      <h2>Event Timeline</h2>

      <div className="timeline">
        {events.map((ev, idx) => {
          const isError =
            ev.event_type?.includes("FAIL") ||
            ev.event_type?.includes("ERROR") ||
            ev.event_type === "WARN";

          return (
            <div key={idx} className={`timeline-item ${isError ? "error" : ""}`}>
              <div className="timeline-meta">
                <span>{ev.timestamp}</span>
                <span>{ev.source}</span>
                <span>{ev.event_type}</span>
              </div>
              <div className="timeline-message">{ev.message}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}