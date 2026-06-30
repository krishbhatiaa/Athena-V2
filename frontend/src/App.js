import React, { useState, useEffect } from 'react';
import { useLiveFeed } from './api';
import WarRoom from './components/WarRoom';
import QuantLab from './components/QuantLab';
import Fundamentals from './components/Fundamentals';
import Agents from './components/Agents';
import RiskMatrix from './components/RiskMatrix';
import Simulator from './components/Simulator';

const TABS = [
  { id: 'war-room', label: 'MARKET WATCH', component: WarRoom },
  { id: 'simulator', label: 'BACKTEST', component: Simulator },
  { id: 'quant-lab', label: 'ANALYTICS', component: QuantLab },
  { id: 'fundamentals', label: 'FUNDAMENTALS', component: Fundamentals },
  { id: 'agents', label: 'AUDIT LOG', component: Agents },
  { id: 'risk-matrix', label: 'RISK', component: RiskMatrix },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('war-room');
  const { connected, lastEvent, simStats } = useLiveFeed();
  const ActiveComponent = TABS.find((t) => t.id === activeTab)?.component || WarRoom;

  return (
    <div style={styles.shell}>
      <StatusBar connected={connected} simStats={simStats} lastEvent={lastEvent} activeTab={activeTab} />
      <div style={styles.body}>
        <nav style={styles.rail} aria-label="ATHENA sections">
          <div style={styles.brand}>
            <div style={styles.brandMark}>ATHENA</div>
            <div style={styles.brandSub}>v2.0</div>
          </div>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{ ...styles.navItem, ...(activeTab === tab.id ? styles.navItemActive : {}) }}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              {tab.label}
            </button>
          ))}
          <div style={styles.railFooter}>
            <div style={styles.disclaimer}>
              PAPER TRADING ONLY
            </div>
          </div>
        </nav>
        <main style={styles.main}>
          <ActiveComponent lastEvent={lastEvent} />
        </main>
      </div>
    </div>
  );
}

function StatusBar({ connected, simStats, lastEvent, activeTab }) {
  const [time, setTime] = useState(() => new Date().toLocaleTimeString('en-US', { hour12: false }));
  useEffect(() => {
    const iv = setInterval(() => setTime(new Date().toLocaleTimeString('en-US', { hour12: false })), 1000);
    return () => clearInterval(iv);
  }, []);
  const tps = simStats?.trades_per_sec ?? 0;
  const equity = simStats?.equity;
  const tab = TABS.find((t) => t.id === activeTab);
  return (
    <header style={styles.bar}>
      <span style={styles.barItem}>
        {connected ? 'CONNECTED' : 'DISCONNECTED'}
      </span>
      <span style={styles.barSep}>|</span>
      <span style={styles.barItem}>{tab?.label || ''}</span>
      <span style={styles.barSep}>|</span>
      {equity != null && (
        <>
          <span style={styles.barItem}>
            SIM EQUITY: ${equity.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </span>
          <span style={styles.barSep}>|</span>
        </>
      )}
      <span style={styles.barItem}>
        TPS: {Math.round(tps).toLocaleString()}
      </span>
      {lastEvent?.type === 'trade_executed' && (
        <>
          <span style={styles.barSep}>|</span>
          <span style={styles.barItem}>
            LAST: <span style={{ color: decisionColor(lastEvent.payload.final_decision) }}>
              {lastEvent.payload.final_decision} {lastEvent.payload.symbol} @ {lastEvent.payload.price}
            </span>
          </span>
        </>
      )}
      <span style={{ flex: 1 }} />
      <span style={styles.barTime}>
        {time}
      </span>
    </header>
  );
}

function decisionColor(d) {
  if (d === 'BUY') return 'var(--signal-buy)';
  if (d === 'SELL') return 'var(--signal-sell)';
  return 'var(--signal-hold)';
}

const styles = {
  shell: { display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--void)', color: 'var(--text-bright)', fontFamily: 'var(--font-mono)', fontSize: 12 },
  bar: {
    display: 'flex', alignItems: 'center', padding: '0 12px', height: 28,
    background: '#1A1E24', borderBottom: '1px solid var(--hairline)',
    flexShrink: 0, fontFamily: 'var(--font-mono)', fontSize: 11, color: '#B8BFC8',
    letterSpacing: '0.03em',
  },
  barItem: { whiteSpace: 'nowrap' },
  barSep: { margin: '0 8px', color: 'var(--text-faint)' },
  barTime: { fontFamily: 'var(--font-mono)', fontSize: 11, color: '#B8BFC8' },
  body: { display: 'flex', flex: 1, minHeight: 0 },
  rail: {
    width: 'var(--rail-width)', flexShrink: 0, display: 'flex', flexDirection: 'column',
    borderRight: '1px solid var(--hairline)', background: 'var(--surface)', padding: '12px 8px',
  },
  brand: { padding: '2px 10px 16px', borderBottom: '1px solid var(--hairline)', marginBottom: 12 },
  brandMark: { fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 13, letterSpacing: '0.12em', color: 'var(--text-bright)' },
  brandSub: { fontSize: 10, color: 'var(--text-faint)', marginTop: 2, letterSpacing: '0.08em' },
  navItem: {
    textAlign: 'left', background: 'transparent', border: 'none', color: 'var(--text-faint)',
    padding: '6px 10px', borderRadius: 0, fontSize: 11, letterSpacing: '0.06em',
    borderLeft: '2px solid transparent',
  },
  navItemActive: { color: 'var(--text-bright)', borderLeftColor: 'var(--signal-hold)', background: 'var(--surface-2)' },
  railFooter: { marginTop: 'auto', paddingTop: 8 },
  disclaimer: { fontSize: 9, color: 'var(--text-faint)', padding: '0 10px', letterSpacing: '0.05em' },
  main: { flex: 1, overflow: 'auto', padding: 16, minWidth: 0 },
};
