import { useEffect, useRef, useState, useCallback } from 'react';

export const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';
const WS_PROTO = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
export const WS_BASE = `${WS_PROTO}//${window.location.host}`;

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json();
}

export const api = {
  health: () => request('/health'),
  quote: (symbol) => request(`/data/quote/${symbol}`),
  history: (symbol, period = '3mo', interval = '1d') =>
    request(`/data/history/${symbol}?period=${period}&interval=${interval}`),
  fundamentals: (symbol) => request(`/data/fundamentals/${symbol}`),
  sentiment: (symbol) => request(`/data/sentiment/${symbol}`),
  macro: () => request('/data/macro'),
  options: (symbol) => request(`/data/options/${symbol}`),

  executeTrade: (symbol) => request(`/trade/execute?symbol=${symbol}`, { method: 'POST' }),
  tradeHistory: (limit = 100) => request(`/trade/history?limit=${limit}`),
  tradeLogs: (limit = 300) => request(`/trade/logs?limit=${limit}`),
  resetTrade: () => request('/trade/reset', { method: 'POST' }),

  blackScholes: (body) => request('/analytics/black-scholes', { method: 'POST', body: JSON.stringify(body) }),
  monteCarlo: (body) => request('/analytics/monte-carlo', { method: 'POST', body: JSON.stringify(body) }),
  hurst: (symbol) => request(`/analytics/hurst/${symbol}`),
  greeksSurface: (symbol, params = '') => request(`/analytics/greeks-surface/${symbol}${params}`),

  riskStatus: () => request('/risk/status'),
  killSwitch: (activate) => request(`/risk/kill-switch?activate=${activate}`, { method: 'POST' }),

  simConfigure: (cfg) => request('/simulate/configure', { method: 'POST', body: JSON.stringify(cfg) }),
  simStart: () => request('/simulate/start', { method: 'POST' }),
  simStop: () => request('/simulate/stop', { method: 'POST' }),
  simReset: () => request('/simulate/reset', { method: 'POST' }),
  simStats: () => request('/simulate/stats'),
};

/** Live WebSocket feed — auto-reconnects, exposes the latest typed events. */
export function useLiveFeed() {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState(null);
  const [simStats, setSimStats] = useState(null);
  const wsRef = useRef(null);
  const retryRef = useRef(0);

  const connect = useCallback(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/live`);
    wsRef.current = ws;

    ws.onopen = () => { setConnected(true); retryRef.current = 0; };
    ws.onclose = (e) => {
      setConnected(false);
      console.warn('WS closed code=%s reason=%s', e.code, e.reason);
      const delay = Math.min(1000 * 2 ** retryRef.current, 10000);
      retryRef.current += 1;
      setTimeout(connect, delay);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data);
        setLastEvent(event);
        if (event.type === 'sim_stats') setSimStats(event.payload);
      } catch {
        // ignore malformed frames
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { connected, lastEvent, simStats };
}
