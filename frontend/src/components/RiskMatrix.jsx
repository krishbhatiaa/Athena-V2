import React, { useState, useEffect, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts';
import { api } from '../api';
import { Card, SectionLabel, ErrMsg, StatBox, GuardrailRow } from './shared';

export default function RiskMatrix({ lastEvent }) {
  const [status, setStatus] = useState(null);
  const [err, setErr] = useState(null);
  const [killing, setKilling] = useState(false);

  const load = useCallback(async () => {
    try { setStatus(await api.riskStatus()); } catch (e) { setErr(e.message); }
  }, []);

  useEffect(() => { load(); const iv = setInterval(load, 3000); return () => clearInterval(iv); }, [load]);
  useEffect(() => { if (lastEvent?.type === 'kill_switch' || lastEvent?.type === 'trade_executed') load(); }, [lastEvent, load]);

  const toggle = async () => {
    setKilling(true);
    try { await api.killSwitch(!status.kill_switch_active); await load(); }
    catch (e) { setErr(e.message); }
    finally { setKilling(false); }
  };

  const reset = async () => {
    try { await api.resetTrade(); await load(); } catch (e) { setErr(e.message); }
  };

  const eqData = (status?.equity_curve || []).map((v, i) => ({ i, equity: v }));
  const dd = status?.drawdown_pct ?? 0;
  const g = status?.guardrails ?? {};
  const killed = status?.kill_switch_active;
  const equity = status?.equity ?? 100000;
  const pl = equity - 100000;
  const plPct = (pl / 100000 * 100).toFixed(2);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <Card style={{ minWidth: 200, borderColor: killed ? 'var(--signal-sell)' : 'var(--hairline)' }}>
          <SectionLabel>KILL SWITCH</SectionLabel>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5, margin: '6px 0 10px' }}>
            {killed
              ? 'All trade execution blocked.' : 'Supervisor evaluating every cycle.'}
          </div>
          <button onClick={toggle} disabled={killing}
            style={{
              width: '100%', border: '1px solid',
              borderColor: killed ? 'var(--signal-buy)' : 'var(--signal-sell)',
              color: killed ? 'var(--signal-buy)' : 'var(--signal-sell)',
              background: killed ? 'var(--buy-dim)' : 'var(--sell-dim)',
              padding: '8px 0', fontSize: 11, letterSpacing: '0.05em',
              cursor: 'pointer', opacity: killing ? 0.5 : 1,
            }}>
            {killing ? 'UPDATING...' : killed ? 'RESUME TRADING' : 'HALT ALL TRADES'}
          </button>
          {err && <ErrMsg style={{ marginTop: 6 }}>{err}</ErrMsg>}
          <button onClick={reset}
            style={{ width: '100%', border: '1px solid var(--hairline)', color: 'var(--text-faint)', background: 'transparent', padding: '6px 0', fontSize: 10, marginTop: 6, cursor: 'pointer' }}>
            RESET HISTORY + EQUITY
          </button>
        </Card>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', flex: 1 }}>
          <StatBox label="PAPER EQUITY" value={`$${equity.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
            color={pl >= 0 ? 'var(--signal-buy)' : 'var(--signal-sell)'}
            sub={`${pl >= 0 ? '+' : ''}${pl.toFixed(2)} (${plPct}%)`} />
          <StatBox label="DRAWDOWN" value={`${dd.toFixed(2)}%`}
            color={dd >= g.max_drawdown_pct ? 'var(--signal-sell)' : dd > g.max_drawdown_pct * 0.7 ? 'var(--signal-hold)' : 'var(--signal-buy)'} />
          <StatBox label="KILL SWITCH" value={killed ? 'HALTED' : 'ACTIVE'}
            color={killed ? 'var(--signal-sell)' : 'var(--signal-buy)'} />
        </div>
      </div>

      <Card>
        <SectionLabel>GUARDRAILS</SectionLabel>
        <div style={{ marginTop: 8 }}>
          {status && (
            <>
              <GuardrailRow label="Kill switch" status={killed ? 'HALTED' : 'OK'} value={killed ? 'BLOCKED' : 'CLEAR'} />
              <GuardrailRow label="Max drawdown" status={dd >= g.max_drawdown_pct ? 'BREACH' : 'OK'} value={`${dd.toFixed(2)}% / ${g.max_drawdown_pct}%`} />
              <GuardrailRow label="Volatility kill" status="OK" value={`threshold ${(g.vol_kill_threshold * 100).toFixed(0)}%`} />
              <GuardrailRow label="Min confidence" status="OK" value={`floor p >= ${g.min_confidence}`} />
              <GuardrailRow label="Max risk score" status="OK" value={`ceiling ${g.max_risk_score}/100`} />
              <GuardrailRow label="Kelly cap" status="OK" value={`<= ${(g.kelly_cap * 100).toFixed(0)}% of account`} />
            </>
          )}
        </div>
      </Card>

      {eqData.length > 1 && (
        <Card style={{ padding: '8px 4px 4px' }}>
          <SectionLabel style={{ paddingLeft: 8 }}>EQUITY CURVE</SectionLabel>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={eqData}>
              <XAxis dataKey="i" hide />
              <YAxis tick={{ fill: 'var(--text-faint)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
                tickLine={false} axisLine={false} width={72}
                tickFormatter={v => `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
                domain={['auto', 'auto']} />
              <Tooltip contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--hairline)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                labelFormatter={() => ''} formatter={v => [`$${v.toFixed(2)}`, 'Equity']} />
              <ReferenceLine y={100000} stroke="var(--hairline)" strokeDasharray="4 4"
                label={{ value: 'START', fill: 'var(--text-faint)', fontSize: 9, fontFamily: 'var(--font-mono)' }} />
              <Line type="monotone" dataKey="equity" stroke={pl >= 0 ? 'var(--signal-buy)' : 'var(--signal-sell)'} dot={false} strokeWidth={1.5} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}
