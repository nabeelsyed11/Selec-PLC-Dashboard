import { useState, useEffect, useRef } from "react";
import { TelemetryMessage } from "../types";

export function useTelemetry() {
  const [data, setData] = useState<TelemetryMessage | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [renderLatencyMs, setRenderLatencyMs] = useState<number>(0);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    function connect() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host || "localhost:8000";
      // If dev server runs on 5173, point to backend 8000
      const wsHost = window.location.port === "5173" ? "localhost:8000" : host;
      const url = `${protocol}//${wsHost}/ws`;

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        const tArrival = performance.now();
        try {
          const parsed: TelemetryMessage = jsonParse(event.data);
          
          // Measure render lag using requestAnimationFrame
          requestAnimationFrame(() => {
            const tRender = performance.now();
            const domRenderLag = Math.max(0, tRender - tArrival);
            setRenderLatencyMs(parseFloat(domRenderLag.toFixed(2)));

            // Send RENDER_ACK back to backend for end-to-end tracing
            if (ws.readyState === WebSocket.OPEN && parsed.t_publish_mono) {
              ws.send(JSON.stringify({
                type: "RENDER_ACK",
                t_publish_mono: parsed.t_publish_mono,
                render_duration_ms: domRenderLag,
                client_id: "dashboard_ui",
              }));
            }
          });

          setData(parsed);
        } catch (e) {
          console.error("Failed to parse telemetry:", e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Auto-reconnect with 2.0s backoff
        reconnectTimeoutRef.current = window.setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { data, isConnected, renderLatencyMs };
}

function jsonParse(str: string): TelemetryMessage {
  return JSON.parse(str);
}
