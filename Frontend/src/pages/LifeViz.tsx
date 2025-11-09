import { useEffect, useState } from "react";


const API_ORIGIN =
  // set this in .env as VITE_API_ORIGIN=http://localhost:8000 for Docker/prod
  (import.meta as any).env?.VITE_API_ORIGIN ??
  `${window.location.protocol}//${window.location.hostname}:8000`;

export default function LiveViz() {
  const params = new URLSearchParams(window.location.search);
  const orderId = params.get("orderId");
  const drug = params.get("drug");
  const [status, setStatus] = useState("connecting…");
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    if (!orderId && !drug) {
      setStatus("missing params");
      return;
    }

    const wsBase = API_ORIGIN.replace(/^http/i, "ws"); // http->ws, https->wss
    const url =
      `${wsBase}/ws/viz?orderId=${encodeURIComponent(orderId ?? "")}` +
      `&drug=${encodeURIComponent(drug ?? "")}`;

    const ws = new WebSocket(url);
    ws.onopen = () => setStatus("live");
    ws.onmessage = (ev) => setData(JSON.parse(ev.data));
    ws.onerror = () => setStatus("error");
    ws.onclose = () => setStatus((s) => (s === "error" ? s : "closed"));
    return () => ws.close();
  }, [orderId, drug]);

  return (
    <div style={{ padding: 24 }}>
      <h2>Live order {orderId ? `#${orderId}` : drug ? `for ${drug}` : ""}</h2>
      <p>Status: {status}</p>
      <pre style={{ background: "#f6f6f6", padding: 12, borderRadius: 8 }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
