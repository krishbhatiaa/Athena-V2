"""
ATHENA high-speed simulator.

No free market-data API can stream real ticks at thousands/sec, so this
engine is explicit about what it is: a *vectorized synthetic backtest*
that stress-tests the strategy logic and infrastructure at high
throughput using simulated Geometric Brownian Motion price paths. The
live, real-data path (routers/trade.py) uses the full 5-agent reasoning
loop against real quotes, at a realistic cadence.

Design for speed:
  - numpy vectorized GBM path generation (no Python-level tick loop)
  - vectorized moving-average crossover signal + Kelly-sized synthetic
    fills computed across an entire batch in one shot
  - batches of N ticks processed per step; only aggregated stats are
    published over the WebSocket (every ~150ms) — never one message
    per trade, which would simply be unrenderable noise downstream
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

import numpy as np

EPS = 1e-12


@dataclass
class SimConfig:
    symbol: str = "SYNTH"
    s0: float = 100.0
    mu: float = 0.08          # annualized drift
    sigma: float = 0.35       # annualized volatility
    ticks_per_batch: int = 2000
    fast_window: int = 8
    slow_window: int = 34
    deadband_bps: float = 8.0  # ignore crossovers smaller than this — avoids fee-bleed on noise
    kelly_fraction: float = 0.1
    fee_bps: float = 0.5      # round-trip cost in basis points, applied per fill


@dataclass
class SimStats:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: float = field(default_factory=time.time)
    total_ticks: int = 0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    equity: float = 100_000.0
    peak_equity: float = 100_000.0
    max_drawdown_pct: float = 0.0
    last_price: float = 0.0
    trades_per_sec: float = 0.0
    equity_curve: list = field(default_factory=lambda: [100_000.0])

    def as_dict(self) -> dict:
        elapsed = max(time.time() - self.started_at, EPS)
        return {
            "run_id": self.run_id,
            "elapsed_sec": elapsed,
            "total_ticks": self.total_ticks,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": (self.wins / self.total_trades) if self.total_trades else 0.0,
            "equity": self.equity,
            "max_drawdown_pct": self.max_drawdown_pct,
            "last_price": self.last_price,
            "trades_per_sec": self.trades_per_sec,
            "avg_ticks_per_sec": self.total_ticks / elapsed,
            "equity_curve_tail": self.equity_curve[-200:],
        }


class SimulationEngine:
    def __init__(self):
        self.config = SimConfig()
        self.stats = SimStats()
        self.running = False
        self._rng = np.random.default_rng()
        self._last_price = self.config.s0
        self._last_signal = 0.0
        self._batch_count = 0

    def configure(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        self.reset()

    def reset(self):
        self.stats = SimStats()
        self._last_price = self.config.s0
        self._last_signal = 0.0
        self.stats.last_price = self._last_price
        self.stats.equity = 100_000.0
        self.stats.peak_equity = 100_000.0
        self._batch_count = 0

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    # ----------------------------------------------------------------
    # Core vectorized batch step — this is what achieves "thousands of
    # trades/sec": one numpy pass evaluates an entire batch of synthetic
    # ticks and signals at once, no per-tick Python overhead.
    # ----------------------------------------------------------------
    def run_batch(self) -> dict:
        cfg = self.config
        n = cfg.ticks_per_batch
        dt = 1.0 / (252 * 6.5 * 3600)  # treat each tick as ~1 simulated second of a trading year

        t0 = time.perf_counter()

        z = self._rng.standard_normal(n)
        log_returns = (cfg.mu - 0.5 * cfg.sigma ** 2) * dt + cfg.sigma * np.sqrt(dt) * z
        prices = self._last_price * np.exp(np.cumsum(log_returns))
        self._last_price = float(prices[-1])

        # Vectorized moving-average crossover, with a deadband so noise-sized
        # gaps between fast/slow don't trigger a fee-incurring flip — only a
        # move bigger than `deadband_bps` counts as a real signal change.
        fast = _rolling_mean(prices, cfg.fast_window)
        slow = _rolling_mean(prices, cfg.slow_window)
        gap_bps = (fast - slow) / np.maximum(slow, EPS) * 10_000
        raw_signal = np.where(gap_bps > cfg.deadband_bps, 1.0,
                      np.where(gap_bps < -cfg.deadband_bps, -1.0, 0.0))

        # Forward-fill: hold the last real signal through the "no clear edge" zone.
        idx = np.arange(n)
        nz_idx = np.where(raw_signal != 0, idx, -1)
        last_nz = np.maximum.accumulate(nz_idx)
        signal = np.where(last_nz < 0, self._last_signal, raw_signal[np.clip(last_nz, 0, None)])

        cross = np.diff(signal, prepend=self._last_signal)
        self._last_signal = float(signal[-1])
        trade_idx = np.nonzero(cross != 0)[0]

        wins = losses = 0
        equity = self.stats.equity
        peak = self.stats.peak_equity
        max_dd = self.stats.max_drawdown_pct
        new_eq_points = []

        if len(trade_idx) > 0:
            entry_prices = prices[trade_idx]
            directions = signal[trade_idx]
            # forward return to the next tick (or last price) as the synthetic fill outcome
            exit_idx = np.minimum(trade_idx + 1, n - 1)
            exit_prices = prices[exit_idx]
            raw_ret = directions * (exit_prices - entry_prices) / np.maximum(entry_prices, EPS)
            fee = cfg.fee_bps / 10_000.0
            net_ret = raw_ret - fee
            pnl_pct = net_ret * cfg.kelly_fraction

            for r in pnl_pct:
                equity *= (1 + r)
                peak = max(peak, equity)
                dd = (peak - equity) / peak * 100 if peak > 0 else 0.0
                max_dd = max(max_dd, dd)
                new_eq_points.append(equity)
                if r > 0:
                    wins += 1
                else:
                    losses += 1

        elapsed_batch = max(time.perf_counter() - t0, EPS)
        self._batch_count += 1

        self.stats.total_ticks += n
        self.stats.total_trades += len(trade_idx)
        self.stats.wins += wins
        self.stats.losses += losses
        self.stats.equity = equity
        self.stats.peak_equity = peak
        self.stats.max_drawdown_pct = max_dd
        self.stats.last_price = self._last_price
        self.stats.trades_per_sec = len(trade_idx) / elapsed_batch
        if new_eq_points:
            self.stats.equity_curve.extend(new_eq_points[-50:])
            self.stats.equity_curve = self.stats.equity_curve[-500:]

        return {
            "batch_trades": int(len(trade_idx)),
            "batch_ticks": n,
            "batch_elapsed_sec": elapsed_batch,
            "instant_trades_per_sec": self.stats.trades_per_sec,
            "instant_ticks_per_sec": n / elapsed_batch,
        }


def _rolling_mean(arr: np.ndarray, window: int) -> np.ndarray:
    """Rolling mean (expanding at the edges) via cumulative sum — fully vectorized."""
    if window <= 1:
        return arr.copy()
    n = len(arr)
    cumsum = np.cumsum(np.insert(arr, 0, 0.0))
    idx = np.arange(n)
    lo = np.maximum(0, idx - window + 1)
    counts = (idx - lo + 1)
    return (cumsum[idx + 1] - cumsum[lo]) / counts


# Single shared engine instance
engine = SimulationEngine()
