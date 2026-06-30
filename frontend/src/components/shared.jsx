import React from 'react';

export function Card({ children, style }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--hairline)', borderRadius: 0, padding: 12, ...style }}>
      {children}
    </div>
  );
}

export function SectionLabel({ children }) {
  return (
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-faint)', marginBottom: 4, marginTop: 8 }}>
      {children}
    </div>
  );
}

export function Pill({ decision, large }) {
  const colors = {
    BUY:  { bg: 'var(--buy-dim)',  fg: 'var(--signal-buy)' },
    SELL: { bg: 'var(--sell-dim)', fg: 'var(--signal-sell)' },
    HOLD: { bg: 'var(--hold-dim)', fg: 'var(--signal-hold)' },
  };
  const c = colors[decision] || colors.HOLD;
  return (
    <span style={{
      color: c.fg,
      fontFamily: 'var(--font-mono)',
      fontWeight: 700,
      fontSize: large ? 14 : 11,
      letterSpacing: '0.06em',
    }}>
      {decision}
    </span>
  );
}

export function Spinner() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 60, color: 'var(--text-faint)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
      REQUESTING...
    </div>
  );
}

export function ErrMsg({ children, style }) {
  return (
    <div style={{ color: 'var(--signal-sell)', fontFamily: 'var(--font-mono)', fontSize: 11, padding: '4px 8px', background: 'var(--sell-dim)', marginTop: 4, ...style }}>
      {children}
    </div>
  );
}

export function KeyVal({ label, value, highlight }) {
  return (
    <span style={{ display: 'inline-flex', flexDirection: 'column', minWidth: 50 }}>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-faint)', letterSpacing: '0.08em' }}>{label}</span>
      <span className="mono" style={{ fontSize: 12, color: highlight || 'var(--text-muted)' }}>{value ?? '--'}</span>
    </span>
  );
}

export function StatBox({ label, value, sub, color }) {
  return (
    <div style={{ background: 'var(--surface-2)', border: '1px solid var(--hairline)', borderRadius: 0, padding: '8px 12px', minWidth: 100 }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-faint)', letterSpacing: '0.08em', marginBottom: 2 }}>{label}</div>
      <div className="mono" style={{ fontSize: 16, fontWeight: 600, color: color || 'var(--text-bright)' }}>{value}</div>
      {sub && <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>{sub}</div>}
    </div>
  );
}

export function GuardrailRow({ label, status, value }) {
  const ok = status === 'OK';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', borderBottom: '1px solid var(--hairline)', fontSize: 12 }}>
      <span style={{ width: 6, height: 6, background: ok ? 'var(--signal-buy)' : 'var(--signal-sell)', flexShrink: 0 }} />
      <span style={{ flex: 1, fontSize: 12 }}>{label}</span>
      <span className="mono" style={{ fontSize: 11, color: ok ? 'var(--signal-buy)' : 'var(--signal-sell)' }}>{status}</span>
      <span className="mono" style={{ fontSize: 10, color: 'var(--text-faint)', minWidth: 50, textAlign: 'right' }}>{value}</span>
    </div>
  );
}

export function Toolbar({ children }) {
  return (
    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center', marginBottom: 8 }}>
      {children}
    </div>
  );
}

export function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? 'var(--surface-2)' : 'transparent',
        color: active ? 'var(--text-bright)' : 'var(--text-faint)',
        border: '1px solid var(--hairline)',
        padding: '3px 10px', fontSize: 11, letterSpacing: '0.05em',
        cursor: 'pointer',
      }}
    >
      {children}
    </button>
  );
}

export function DataTable({ columns, rows }) {
  return (
    <table>
      <thead>
        <tr>
          {columns.map((col, i) => <th key={i}>{col}</th>)}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>
            {row.map((cell, j) => <td key={j}>{cell}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
