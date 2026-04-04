const API_BASE = "";

export async function startSession(p, g) {
  const res = await fetch(`${API_BASE}/api/session/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ p, g }),
  });

  if (!res.ok) {
    throw new Error(`Start session failed: ${res.status}`);
  }

  return res.json();
}

export async function resetSession() {
  const res = await fetch(`${API_BASE}/api/session/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });

  if (!res.ok) {
    throw new Error(`Reset session failed: ${res.status}`);
  }

  return res.json();
}

export function createSocket(onMessage) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

  ws.onopen = () => {
    console.log("WebSocket connected");
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    onMessage(msg);
  };

  ws.onerror = (err) => {
    console.error("WebSocket error", err);
  };

  ws.onclose = () => {
    console.warn("WebSocket closed");
  };

  return ws;
}