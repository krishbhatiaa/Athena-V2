import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import { Card, SectionLabel, ErrMsg, KeyVal, Spinner, StatBox, TabButton } from './shared';

const SYMBOLS = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'AMZN', 'GOOG', 'SPY', 'QQQ'];

export default function Fundamentals() {
  const [symbol, setSymbol] = useState('AAPL');
  const [input, setInput] = useState('AAPL');
  const [fund, setFund] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [hurst, setHurst] = useState(null);
  const [macro, setMacro] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const load = useCallback(async (sym) => {
    setLoading(true); setErr(null);
    try {
      const [f, s, h, m] = await Promise.all([
        api.fundamentals(sym),
        api.sentiment(sym),
        api.hurst(sym),
        api.macro(),
      ]);
      setFund(f); setSentiment(s); setHurst(h); setMacro(m);
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(symbol); }, [symbol, load]);

  const go = (s) => { const sym = s.trim().toUpperCase(); if (sym) { setSymbol(sym); setInput(sym); } };

  const sentColor = sentiment?.label === 'bullish' ? 'var(--signal-buy)' : sentiment?.label === 'bearish' ? 'var(--signal-sell)' : 'var(--signal-hold)';
  const hColor = hurst?.regime === 'trending' ? 'var(--signal-buy)' : hurst?.regime === 'mean_reverting' ? 'var(--signal-sell)' : 'var(--signal-hold)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
        <SectionLabel>SYMBOL</SectionLabel>
        {SYMBOLS.map(s => (
          <TabButton key={s} active={s === symbol} onClick={() => go(s)}>{s}</TabButton>
        ))}
        <form onSubmit={e => { e.preventDefault(); go(input); }} style={{ display: 'flex', gap: 4, marginLeft: 4 }}>
          <input value={input} onChange={e => setInput(e.target.value.toUpperCase())} placeholder="TICKER" style={{ width: 80 }} maxLength={10} />
          <button type="submit" style={{ background: 'var(--surface-2)', border: '1px solid var(--hairline)', color: 'var(--text-muted)', padding: '3px 8px', fontSize: 11 }}>GO</button>
        </form>
      </div>

      {loading && <Spinner />}
      {err && <ErrMsg>{err}</ErrMsg>}

      {fund && (
        <Card>
          <SectionLabel>COMPANY</SectionLabel>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 6 }}>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{symbol}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 1 }}>{fund.name}</div>
              <div style={{ fontSize: 11, color: 'var(--text-faint)', marginTop: 1 }}>{fund.sector} &middot; {fund.industry}</div>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', flex: 1 }}>
              <KeyVal label="P/E" value={fund.pe_ratio?.toFixed(1) ?? '--'} />
              <KeyVal label="FWD P/E" value={fund.forward_pe?.toFixed(1) ?? '--'} />
              <KeyVal label="P/B" value={fund.pb_ratio?.toFixed(2) ?? '--'} />
              <KeyVal label="ROE" value={fund.roe != null ? `${(fund.roe * 100).toFixed(1)}%` : '--'} />
              <KeyVal label="BETA" value={fund.beta?.toFixed(2) ?? '--'} />
              <KeyVal label="DIV YLD" value={fund.dividend_yield != null ? `${(fund.dividend_yield * 100).toFixed(2)}%` : '--'} />
              <KeyVal label="MKT CAP" value={fund.market_cap ? `$${(fund.market_cap / 1e9).toFixed(1)}B` : '--'} />
              <KeyVal label="52W HIGH" value={fund['52w_high']?.toFixed(2) ?? '--'} />
              <KeyVal label="52W LOW" value={fund['52w_low']?.toFixed(2) ?? '--'} />
            </div>
          </div>
        </Card>
      )}

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        {hurst && (
          <Card style={{ flex: 1, minWidth: 240 }}>
            <SectionLabel>HURST EXPONENT</SectionLabel>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 8 }}>
              <StatBox label="HURST" value={hurst.hurst.toFixed(3)} color={hColor} />
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: hColor, fontFamily: 'var(--font-mono)', letterSpacing: '0.06em', marginBottom: 4 }}>
                  {hurst.regime?.replace('_', ' ')}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  H &lt; 0.45 mean reverting &middot; H &asymp; 0.5 random walk &middot; H &gt; 0.55 trending.
                </div>
              </div>
            </div>
          </Card>
        )}

        {sentiment && (
          <Card style={{ flex: 1, minWidth: 240 }}>
            <SectionLabel>SENTIMENT</SectionLabel>
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginTop: 8 }}>
              <StatBox label="SCORE" value={sentiment.score.toFixed(3)} color={sentColor} sub={sentiment.label?.toUpperCase()} />
              <div style={{ flex: 1 }}>
                {sentiment.headlines.slice(0, 5).map((h, i) => (
                  <div key={i} style={{ display: 'flex', gap: 6, padding: '3px 0', borderBottom: '1px solid var(--hairline)', alignItems: 'baseline', fontSize: 11 }}>
                    <span className="mono" style={{ color: h.score > 0 ? 'var(--signal-buy)' : h.score < 0 ? 'var(--signal-sell)' : 'var(--text-faint)', minWidth: 36, flexShrink: 0 }}>
                      {h.score > 0 ? '+' : ''}{h.score.toFixed(2)}
                    </span>
                    <span style={{ color: 'var(--text-muted)' }}>{h.title}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        )}
      </div>

      {macro && (
        <Card>
          <SectionLabel>MACRO</SectionLabel>
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginTop: 8 }}>
            <KeyVal label="VIX" value={macro.vix?.toFixed(2) ?? '--'} />
            <KeyVal label="10Y YIELD" value={macro.yield_10y ? `${macro.yield_10y.toFixed(3)}%` : '--'} />
            <KeyVal label="DXY" value={macro.dollar_index?.toFixed(2) ?? '--'} />
            <KeyVal label="GOLD" value={macro.gold ? `$${macro.gold.toFixed(0)}` : '--'} />
            <KeyVal label="OIL" value={macro.oil ? `$${macro.oil.toFixed(2)}` : '--'} />
          </div>
        </Card>
      )}
    </div>
  );
}
