import React, { useState } from 'react';
import { api } from '../api';
import { Card, SectionLabel, ErrMsg, StatBox, KeyVal } from './shared';

export default function QuantLab() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <BlackScholes />
      <MonteCarlo />
    </div>
  );
}

function BlackScholes() {
  const [form, setForm] = useState({ S: 210, K: 215, T: 0.25, r: 0.045, sigma: 0.28, option_type: 'call' });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const calc = async () => {
    setLoading(true); setErr(null);
    try { setResult(await api.blackScholes({ ...form, T: parseFloat(form.T), S: parseFloat(form.S), K: parseFloat(form.K), r: parseFloat(form.r), sigma: parseFloat(form.sigma) })); }
    catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const update = (k, v) => setForm(f => ({ ...f, [k]: v }));

  return (
    <Card>
      <SectionLabel>BLACK-SCHOLES PRICER</SectionLabel>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start', marginTop: 8 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, flex: 1, minWidth: 280 }}>
          {[
            ['S', 'Spot Price ($)', 1],
            ['K', 'Strike Price ($)', 1],
            ['T', 'Time to Expiry (yrs)', 0.01],
            ['r', 'Risk-Free Rate', 0.001],
            ['sigma', 'Implied Vol', 0.01],
          ].map(([key, label, step]) => (
            <label key={key} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span style={{ fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>{label}</span>
              <input type="number" value={form[key]} step={step}
                onChange={e => update(key, parseFloat(e.target.value))} style={inputStyle} />
            </label>
          ))}
          <label style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>Type</span>
            <select value={form.option_type} onChange={e => update('option_type', e.target.value)} style={inputStyle}>
              <option value="call">CALL</option>
              <option value="put">PUT</option>
            </select>
          </label>
        </div>
        {result && (
          <div style={{ flex: 1, minWidth: 240 }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
              <StatBox label="PRICE" value={`$${result.price.toFixed(4)}`} color="var(--text-bright)" />
              <StatBox label="D1" value={result.d1.toFixed(4)} />
              <StatBox label="D2" value={result.d2.toFixed(4)} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6 }}>
              {Object.entries(result.greeks).map(([g, v]) => (
                <KeyVal key={g} label={g.toUpperCase()} value={v.toFixed(4)} />
              ))}
            </div>
          </div>
        )}
      </div>
      {err && <ErrMsg>{err}</ErrMsg>}
      <button onClick={calc} disabled={loading}
        style={{ marginTop: 10, padding: '6px 20px', background: 'var(--surface-3)', border: '1px solid var(--hairline)', color: 'var(--text-bright)', fontSize: 11, letterSpacing: '0.05em', cursor: 'pointer', opacity: loading ? 0.5 : 1 }}>
        {loading ? 'COMPUTING...' : 'COMPUTE'}
      </button>
    </Card>
  );
}

function MonteCarlo() {
  const [form, setForm] = useState({ S0: 100, mu: 0.08, sigma: 0.25, T: 1.0, steps: 252, sims: 3000 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const run = async () => {
    setLoading(true); setErr(null);
    try { setResult(await api.monteCarlo({ S0: +form.S0, mu: +form.mu, sigma: +form.sigma, T: +form.T, steps: +form.steps, sims: +form.sims })); }
    catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const update = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const terminalDist = result ? Object.entries(result.percentiles).map(([p, v]) => ({ pct: `p${p}`, price: v })) : [];

  return (
    <Card>
      <SectionLabel>MONTE CARLO SIMULATION</SectionLabel>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start', marginTop: 8 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, flex: 1, minWidth: 280 }}>
          {[
            ['S0', 'Start Price ($)', 1],
            ['mu', 'Annual Drift', 0.01],
            ['sigma', 'Annual Vol', 0.01],
            ['T', 'Horizon (yrs)', 0.25],
            ['steps', 'Time Steps', 1],
            ['sims', 'Simulations', 100],
          ].map(([key, label, step]) => (
            <label key={key} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span style={{ fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>{label}</span>
              <input type="number" value={form[key]} step={step}
                onChange={e => update(key, e.target.value)} style={inputStyle} />
            </label>
          ))}
        </div>
        {result && (
          <div style={{ flex: 1, minWidth: 240, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <StatBox label="EXPECTED" value={`$${result.expected_price.toFixed(2)}`} />
              <StatBox label="VaR 95" value={`${(result.var_95 * 100).toFixed(2)}%`} color="var(--signal-sell)" />
              <StatBox label="CVaR 95" value={`${(result.cvar_95 * 100).toFixed(2)}%`} color="var(--signal-sell)" />
              <StatBox label="SHARPE" value={result.sharpe.toFixed(3)} color={result.sharpe > 1 ? 'var(--signal-buy)' : 'var(--text-bright)'} />
              <StatBox label="SORTINO" value={result.sortino.toFixed(3)} />
              <StatBox label="P(PROFIT)" value={`${(result.p_profit * 100).toFixed(1)}%`} color="var(--text-bright)" />
            </div>
            {terminalDist.length > 0 && (
              <div>
                <SectionLabel>TERMINAL PERCENTILES</SectionLabel>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 4 }}>
                  {terminalDist.map(({ pct, price }) => (
                    <KeyVal key={pct} label={pct.toUpperCase()} value={`$${price.toFixed(2)}`} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      {err && <ErrMsg>{err}</ErrMsg>}
      <button onClick={run} disabled={loading}
        style={{ marginTop: 10, padding: '6px 20px', background: 'var(--surface-3)', border: '1px solid var(--hairline)', color: 'var(--text-bright)', fontSize: 11, letterSpacing: '0.05em', cursor: 'pointer', opacity: loading ? 0.5 : 1 }}>
        {loading ? `RUNNING ${(+form.sims).toLocaleString()} PATHS...` : 'RUN SIMULATION'}
      </button>
    </Card>
  );
}

const inputStyle = { background: 'var(--surface-2)', border: '1px solid var(--hairline)', color: 'var(--text-bright)', padding: '4px 6px', fontFamily: 'var(--font-mono)', fontSize: 11, width: '100%' };
