import { useState, useEffect, useRef } from "react";

export interface ExecutionEvent {
  event_id: string;
  execution_id: string;
  workflow_id: string;
  tenant_id: string;
  sequence: number;
  timestamp: number;
  event_type: string;
  node_id?: string;
  agent_run_id?: string;
  payload: Record<string, any>;
}

export function useExecutionStream(executionId: string | null | undefined, organizationId: string, token?: string) {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected">("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const lastSeqRef = useRef<number>(0);

  useEffect(() => {
    // Clear previous execution session data
    setEvents([]);
    lastSeqRef.current = 0;

    if (!executionId) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setStatus("disconnected");
      return;
    }

    const connect = () => {
      setStatus("connecting");
      const url = `ws://${window.location.host}/api/v1/debug/ws?execution_id=${executionId}&tenant_id=${organizationId}&last_sequence=${lastSeqRef.current}${token ? `&token=${token}` : ""}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
      };

      ws.onmessage = (event) => {
        try {
          const envelope: ExecutionEvent = JSON.parse(event.data);
          setEvents((prev) => {
            // Avoid duplicate sequences
            if (prev.some((e) => e.sequence === envelope.sequence)) {
              return prev;
            }
            const updated = [...prev, envelope].sort((a, b) => a.sequence - b.sequence);
            lastSeqRef.current = updated[updated.length - 1]?.sequence || 0;
            return updated;
          });
        } catch (err) {
          console.error("Failed to parse websocket execution event:", err);
        }
      };

      ws.onclose = () => {
        setStatus("disconnected");
        // Try reconnecting after 3 seconds
        setTimeout(() => {
          if (wsRef.current === ws) {
            connect();
          }
        }, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [executionId, organizationId, token]);

  return { events, status };
}
