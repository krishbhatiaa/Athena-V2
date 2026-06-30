import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import { SectionLabel, ErrMsg, Spinner, TabButton } from './shared';

const ROLES = ['Trader', 'Analyst', 'Risk', 'Supervisor', 'Content', 'Explain'];

const PHASE_ORDER = ['PLAN', 'ANALYZE', 'RISK', 'EXECUTE', 'AUDIT', 'CONTENT', 'EXPLAIN'];

export default function Agents({ lastEvent }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);
  const [filter, setFilter] = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    try { setLogs(await api.tradeLogs(300)); }
    catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (lastEvent?.type === 'trade_executed') load(); }, [lastEvent, load]);

  const filtered = filter ? logs.filter(l => l.agent === filter) : logs;
  const recent = [...filtered].reverse().slice(0, 80);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        <SectionLabel>ROLE FILTER</SectionLabel>
        {ROLES.map(r => (
          <TabButton key={r} active={filter === r} onClick={() => setFilter(filter === r ? null : r)}>
            {r.toUpperCase()}
          </TabButton>
        ))}
        <button onClick={load} style={{ background: 'transparent', border: '1px solid var(--hairline)', color: 'var(--text-muted)', padding: '3px 8px', fontSize: 10, marginLeft: 4, cursor: 'pointer' }}>
          REFRESH
        </button>
      </div>

      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
        <SectionLabel>PHASE</SectionLabel>
        {PHASE_ORDER.map(p => (
          <span key={p} className="mono" style={{ fontSize: 9, color: 'var(--text-faint)', padding: '1px 5px', border: '1px solid var(--hairline)' }}>{p}</span>
        ))}
      </div>

      {loading && <Spinner />}
      {err && <ErrMsg>{err}</ErrMsg>}
      {!loading && !err && recent.length === 0 && (
        <div style={{ color: 'var(--text-faint)', fontFamily: 'var(--font-mono)', fontSize: 11, padding: 20, textAlign: 'center' }}>
          No entries yet &mdash; run a cycle from MARKET WATCH.
        </div>
      )}

      <div style={{ maxHeight: 560, overflowY: 'auto', borderTop: '1px solid var(--hairline)' }}>
        {recent.map((log, i) => (
          <div key={i} style={{ display: 'flex', gap: 8, padding: '4px 6px', borderBottom: '1px solid var(--hairline)', fontSize: 11, alignItems: 'flex-start' }}>
            <span className="mono" style={{ color: 'var(--text-faint)', whiteSpace: 'nowrap', flexShrink: 0 }}>
              {new Date(log._ts * 1000).toISOString().slice(11, 19)}
            </span>
            <span className="mono" style={{ color: 'var(--text-faint)', width: 60, flexShrink: 0 }}>{log.phase}</span>
            <span className="mono" style={{ color: 'var(--text-bright)', width: 100, flexShrink: 0 }}>{log.agent}</span>
            <span style={{ color: 'var(--text-muted)' }}>{log.summary}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
