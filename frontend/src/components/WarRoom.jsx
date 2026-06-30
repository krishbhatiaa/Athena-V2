import React, { useState, useEffect, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Brush } from 'recharts';
import { api } from '../api';
import { Card, SectionLabel, Pill, Spinner, ErrMsg, KeyVal, Toolbar, TabButton } from './shared';

const SYMBOLS = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'SPY', 'QQQ', 'AMZN', 'GOOG'];

export default function WarRoom({ lastEvent }) {
  const [symbol, setSymbol] = useState('AAPL');
  const [input, setInput] = useState('AAPL');
  const [history, setHistory] = useState(null);
  const [quote, setQuote] = useState(null);
  const [tradeResult, setTradeResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [err, setErr] = useState(null);
  const [tradeHistory, setTradeHistory] = useState([]);

  const loadChart = useCallback(async (sym) => {
    setLoading(true); setErr(null);
    try {
      const [h, q] = await Promise.all([api.history(sym), api.quote(sym)]);
      setHistory(h); setQuote(q);
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  }, []);

  const loadHistory = useCallback(async () => {
    try { setTradeHistory(await api.tradeHistory(20)); } catch {}
  }, []);

  useEffect(() => { loadChart(symbol); loadHistory(); }, [symbol, loadChart, loadHistory]);

  useEffect(() => {
    if (lastEvent?.type === 'trade_executed') loadHistory();
  }, [lastEvent, loadHistory]);

  const execute = async () => {
    setExecuting(true); setErr(null); setTradeResult(null);
    try { setTradeResult(await api.executeTrade(symbol)); loadHistory(); }
    catch (e) { setErr(e.message); }
    finally { setExecuting(false); }
  };

  const go = (sym) => { const s = sym.trim().toUpperCase(); if (s) { setSymbol(s); setInput(s); } };

  const chartData = history ? history.dates.map((d, i) => ({
    date: d.slice(5), close: history.close[i],
  })) : [];

  const changeAbs = quote ? (quote.price - quote.previous_close).toFixed(2) : null;
  const changePct = quote ? ((quote.price - quote.previous_close) / quote.previous_close * 100).toFixed(2) : null;
  const up = changeAbs > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Toolbar>
        <SectionLabel>MARKET</SectionLabel>
        {SYMBOLS.map(s => (
          <TabButton key={s} active={s === symbol} onClick={() => go(s)}>{s}</TabButton>
        ))}
        <form onSubmit={e => { e.preventDefault(); go(input); }} style={{ display: 'flex', gap: 4, marginLeft: 4 }}>
          <input value={input} onChange={e => setInput(e.target.value.toUpperCase())}
            placeholder="TICKER" style={{ width: 80 }} maxLength={10} />
          <button type="submit" style={{ background: 'var(--surface-2)', border: '1px solid var(--hairline)', color: 'var(--text-muted)', padding: '3px 8px', fontSize: 11 }}>GO</button>
        </form>
      </Toolbar>

      {quote && (
        <Card>
          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'baseline' }}>
            <span className="mono" style={{ fontSize: 22, fontWeight: 700 }}>{symbol}</span>
            <span className="mono" style={{ fontSize: 20 }}>${quote.price?.toFixed(2)}</span>
            <span className="mono" style={{ fontSize: 13, color: up ? 'var(--signal-buy)' : 'var(--signal-sell)' }}>
              {changeAbs} ({changePct}%)
            </span>
            <KeyVal label="HIGH" value={quote.day_high?.toFixed(2)} />
            <KeyVal label="LOW" value={quote.day_low?.toFixed(2)} />
            <KeyVal label="VOL" value={quote.volume?.toLocaleString()} />
          </div>
        </Card>
      )}

      <Card style={{ padding: '8px 4px 4px' }}>
        {loading && <Spinner />}
        {err && <ErrMsg>{err}</ErrMsg>}
        {!loading && !err && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
              <XAxis dataKey="date" tick={{ fill: 'var(--text-faint)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                tickLine={false} axisLine={{ stroke: 'var(--hairline)' }} interval="preserveStartEnd" />
              <YAxis tick={{ fill: 'var(--text-faint)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                tickLine={false} axisLine={false} domain={['auto', 'auto']} width={56}
                tickFormatter={v => `$${v.toFixed(0)}`} />
              <Tooltip contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--hairline)', borderRadius: 0, fontSize: 11, fontFamily: 'var(--font-mono)' }}
                labelStyle={{ color: 'var(--text-muted)' }}
                itemStyle={{ color: 'var(--text-bright)' }} />
              <Line type="monotone" dataKey="close" stroke="var(--signal-info)" dot={false} strokeWidth={1.5} />
              <Brush dataKey="date" height={16} stroke="var(--hairline)" fill="var(--surface)"
                travellerWidth={6} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <Card style={{ flex: 1, minWidth: 260 }}>
          <SectionLabel>EXECUTION</SectionLabel>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6, margin: '6px 0' }}>
            Runs the trading pipeline against {symbol} market data.
          </p>
          <button onClick={execute} disabled={executing}
            style={{
              marginTop: 8, width: '100%',
              background: executing ? 'var(--surface-2)' : 'var(--surface-3)',
              border: '1px solid var(--hairline)', color: 'var(--text-bright)',
              padding: '8px 0', fontSize: 12, letterSpacing: '0.05em', cursor: 'pointer',
            }}>
            {executing ? 'PROCESSING...' : `RUN — ${symbol}`}
          </button>
          {err && <ErrMsg style={{ marginTop: 8 }}>{err}</ErrMsg>}
        </Card>

        {tradeResult && (
          <Card style={{ flex: 2, minWidth: 320 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span className="mono" style={{ fontSize: 11, color: 'var(--text-faint)' }}>CYCLE {tradeResult.cycle_id}</span>
              <Pill decision={tradeResult.final_decision} large />
              <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {tradeResult.symbol} @ ${tradeResult.price?.toFixed(2)}
              </span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: 8 }}>
              {tradeResult.explain}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, maxHeight: 160, overflowY: 'auto' }}>
              {tradeResult.messages.map((m, i) => (
                <div key={i} style={{ display: 'flex', gap: 6, padding: '2px 0', borderBottom: '1px solid var(--hairline)', fontSize: 11 }}>
                  <span className="mono" style={{ color: 'var(--text-faint)', width: 70, flexShrink: 0 }}>{m.phase}</span>
                  <span style={{ color: 'var(--text-muted)' }}>[{m.agent}] {m.summary}</span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>

      {tradeHistory.length > 0 && (
        <Card>
          <SectionLabel>RECENT CYCLES</SectionLabel>
          <div style={{ overflowX: 'auto', marginTop: 4 }}>
            <table>
              <thead>
                <tr><th>CYCLE</th><th>SYMBOL</th><th>PRICE</th><th>DECISION</th><th>EXPLANATION</th></tr>
              </thead>
              <tbody>
                {tradeHistory.slice().reverse().map((t, i) => (
                  <tr key={i}>
                    <td className="mono">{t.cycle_id}</td>
                    <td className="mono">{t.symbol}</td>
                    <td className="mono">${t.price?.toFixed(2)}</td>
                    <td><Pill decision={t.final_decision} /></td>
                    <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.explain}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
