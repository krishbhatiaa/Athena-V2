import React, { useState, useEffect, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../api';
import { Card, SectionLabel, StatBox, ErrMsg } from './shared';

export default function Simulator({ lastEvent }) {
  const [running, setRunning] = useState(false);
  const [stats, setStats] = useState(null);
  const [err, setErr] = useState(null);
  const [cfg, setCfg] = useState({ sigma: 0.35, mu: 0.08, ticks_per_batch: 2000, fee_bps: 0.5, kelly_fraction: 0.1, deadband_bps: 8.0 });

  const refreshStats = useCallback(async () => {
    try { setStats(await api.simStats()); } catch {}
  }, []);

  useEffect(() => {
    refreshStats();
    const iv = setInterval(refreshStats, 2000);
    return () => clearInterval(iv);
  }, [refreshStats]);

  useEffect(() => {
    if (lastEvent?.type === 'sim_stats') setStats(lastEvent.payload);
  }, [lastEvent]);

  const start = async () => {
    setErr(null);
    try {
      await api.simConfigure(cfg);
      await api.simStart();
      setRunning(true);
    } catch (e) { setErr(e.message); }
  };

  const stop = async () => {
    try { await api.simStop(); setRunning(false); } catch (e) { setErr(e.message); }
  };

  const reset = async () => {
    try { await api.simReset(); setStats(null); setRunning(false); } catch (e) { setErr(e.message); }
  };

  const eqCurve = (stats?.equity_curve_tail || []).map((v, i) => ({ i, equity: v }));
  const tps = stats?.trades_per_sec ?? 0;
  const tpsStr = tps >= 1000 ? `${(tps / 1000).toFixed(1)}K` : Math.round(tps).toString();
  const ticksStr = stats?.total_ticks ? `${(stats.total_ticks / 1e6).toFixed(2)}M` : '0';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <Card style={{ flex: 1, minWidth: 280 }}>
          <SectionLabel>CONFIGURATION</SectionLabel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 6 }}>
            {[
              { key: 'sigma', label: 'Annual Vol', step: 0.01, min: 0.01, max: 2 },
              { key: 'mu', label: 'Annual Drift', step: 0.01, min: -1, max: 2 },
              { key: 'ticks_per_batch', label: 'Ticks/Batch', step: 500, min: 100, max: 50000 },
              { key: 'deadband_bps', label: 'Signal Deadband (bps)', step: 1, min: 0, max: 100 },
              { key: 'kelly_fraction', label: 'Kelly Fraction', step: 0.01, min: 0.01, max: 0.5 },
              { key: 'fee_bps', label: 'Fee (bps)', step: 0.1, min: 0, max: 20 },
            ].map(({ key, label, step, min, max }) => (
              <label key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, color: 'var(--text-muted)' }}>
                <span>{label}</span>
                <input type="number" value={cfg[key]} step={step} min={min} max={max}
                  onChange={e => setCfg(c => ({ ...c, [key]: parseFloat(e.target.value) || 0 }))}
                  disabled={running}
                  style={{ ...numInput, opacity: running ? 0.4 : 1 }} />
              </label>
            ))}
          </div>
          {err && <ErrMsg style={{ marginTop: 8 }}>{err}</ErrMsg>}
          <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
            <button onClick={running ? stop : start}
              style={{ flex: 2, border: '1px solid', borderColor: running ? 'var(--signal-sell)' : 'var(--signal-buy)', color: running ? 'var(--signal-sell)' : 'var(--signal-buy)', background: running ? 'var(--sell-dim)' : 'var(--buy-dim)', padding: '6px 0', fontSize: 11, letterSpacing: '0.05em', cursor: 'pointer' }}>
              {running ? 'STOP' : 'START'}
            </button>
            <button onClick={reset} disabled={running}
              style={{ flex: 1, border: '1px solid var(--hairline)', color: 'var(--text-muted)', background: 'transparent', padding: '6px 0', fontSize: 11, cursor: 'pointer', opacity: running ? 0.4 : 1 }}>
              RESET
            </button>
          </div>
        </Card>

        <div style={{ flex: 2, minWidth: 320, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <StatBox label="TRADES/SEC" value={tpsStr} color={running ? 'var(--signal-buy)' : 'var(--text-muted)'} />
            <StatBox label="TICKS" value={ticksStr} />
            <StatBox label="TRADES" value={stats?.total_trades?.toLocaleString() ?? '0'} />
            <StatBox label="WIN RATE" value={stats?.win_rate ? `${(stats.win_rate * 100).toFixed(1)}%` : '--'} sub={`${stats?.wins ?? 0}W / ${stats?.losses ?? 0}L`} />
            <StatBox label="EQUITY"
              value={stats?.equity ? `$${Math.round(stats.equity).toLocaleString()}` : '--'}
              color={stats?.equity > 100000 ? 'var(--signal-buy)' : stats?.equity < 100000 ? 'var(--signal-sell)' : 'var(--text-bright)'}
              sub={`dd ${stats?.max_drawdown_pct?.toFixed(2) ?? '0.00'}%`} />
          </div>

          {eqCurve.length > 1 && (
            <Card style={{ padding: '8px 4px 4px' }}>
              <SectionLabel style={{ paddingLeft: 8 }}>EQUITY CURVE</SectionLabel>
              <ResponsiveContainer width="100%" height={140}>
                <LineChart data={eqCurve}>
                  <XAxis dataKey="i" hide />
                  <YAxis tick={{ fill: 'var(--text-faint)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
                    tickLine={false} axisLine={false} width={60}
                    tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} domain={['auto', 'auto']} />
                  <Tooltip contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--hairline)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                    labelFormatter={() => ''} formatter={v => [`$${v.toFixed(2)}`, 'Equity']} />
                  <Line type="monotone" dataKey="equity" stroke="var(--signal-buy)" dot={false} strokeWidth={1.5} />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          )}
        </div>
      </div>

      <Card>
        <SectionLabel>METHOD</SectionLabel>
        <p style={{ fontSize: 11, lineHeight: 1.7, color: 'var(--text-muted)', margin: '6px 0 0' }}>
          Vectorized GBM tick generation with MA crossover signal. Deadband filters whipsaw trades.
          Kelly-sized positions. Single numpy pass per batch &mdash; no Python-level tick loop.
        </p>
      </Card>
    </div>
  );
}

const numInput = { background: 'var(--surface-2)', border: '1px solid var(--hairline)', color: 'var(--text-bright)', padding: '2px 6px', fontFamily: 'var(--font-mono)', fontSize: 11, width: 80, textAlign: 'right' };
