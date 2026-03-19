/**
 * useWebSocket – React hook for the AlgoPlatform real-time WebSocket feed.
 *
 * Connects to /ws/prices on the backend, handles reconnection automatically,
 * and exposes:
 *
 *   prices    – { [symbol]: { price, change, change_pct, high, low, volume, ... } }
 *   connected – boolean
 *   lastSignal – latest strategy_signal payload (or null)
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL = BASE_URL.replace(/^http/, 'ws');   // http → ws, https → wss

const RECONNECT_DELAY_MS = 5_000;

export function useWebSocket() {
  const [prices, setPrices] = useState({});
  const [connected, setConnected] = useState(false);
  const [lastSignal, setLastSignal] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const unmountedRef = useRef(false);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_URL}/ws/prices`);
    wsRef.current = ws;

    ws.onopen = () => {
      if (unmountedRef.current) { ws.close(); return; }
      setConnected(true);
      // Start a heartbeat so the server doesn't drop a silent connection.
      ws._heartbeatTimer = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 30_000);
    };

    ws.onclose = () => {
      clearInterval(ws._heartbeatTimer);
      if (unmountedRef.current) return;
      setConnected(false);
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
    };

    ws.onerror = () => {
      // onclose will fire right after, which triggers reconnect.
      ws.close();
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'price_update') {
          setPrices((prev) => ({ ...prev, ...msg.data }));
        } else if (msg.type === 'strategy_signal') {
          setLastSignal({ ...msg.data, _ts: msg.timestamp });
        }
      } catch {
        // ignore malformed frames
      }
    };
  }, []);

  useEffect(() => {
    unmountedRef.current = false;
    connect();
    return () => {
      unmountedRef.current = true;
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        clearInterval(wsRef.current._heartbeatTimer);
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { prices, connected, lastSignal };
}
