import { useEffect, useRef, useState } from "react";

import type { SocketMessage } from "../types";

export type SocketStatus = "connecting" | "open" | "closed";

function wsUrl(storyId: string, token?: string): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const base = `${proto}://${window.location.host}/ws/stories/${storyId}`;
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
}

// Opens a resilient WebSocket for a story and forwards parsed messages.
// Automatically reconnects (with a small delay) while the component is mounted.
export function useGameSocket(
  storyId: string | undefined,
  token: string | undefined,
  onMessage: (msg: SocketMessage) => void
): SocketStatus {
  const [status, setStatus] = useState<SocketStatus>("connecting");
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  useEffect(() => {
    if (!storyId) return;
    let closedByUs = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let pingTimer: ReturnType<typeof setInterval> | undefined;

    const connect = () => {
      setStatus("connecting");
      socket = new WebSocket(wsUrl(storyId, token));

      socket.onopen = () => {
        setStatus("open");
        pingTimer = setInterval(() => {
          if (socket && socket.readyState === WebSocket.OPEN) socket.send("ping");
        }, 25000);
      };

      socket.onmessage = (event) => {
        if (event.data === "pong") return;
        try {
          const msg = JSON.parse(event.data) as SocketMessage;
          handlerRef.current(msg);
        } catch {
          /* ignore malformed frames */
        }
      };

      socket.onclose = () => {
        setStatus("closed");
        if (pingTimer) clearInterval(pingTimer);
        if (!closedByUs) {
          reconnectTimer = setTimeout(connect, 1500);
        }
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      closedByUs = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (pingTimer) clearInterval(pingTimer);
      socket?.close();
    };
  }, [storyId, token]);

  return status;
}
