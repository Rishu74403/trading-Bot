"""Tests for backtester."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np

from bot.backtester import Backtester, compare_strategies
from bot.strategies import SMACrossover, get_strategy, list_strategies
from bot.portfolio import Portfolio


@pytest.fixture
def sample_df():
    np.random.seed(42)
    n = 200
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="h"),
        "datetime": pd.date_range("2025-01-01", periods=n, freq="h"),
        "open": close + np.random.randn(n) * 0.5,
        "high": close + abs(np.random.randn(n)) * 2,
        "low": close - abs(np.random.randn(n)) * 2,
        "close": close,
        "volume": np.random.randint(1000, 10000, n).astype(float),
    })


class TestBacktester:
    def test_run_returns_result(self, sample_df):
        strategy = SMACrossover(fast_period=10, slow_period=30)
        bt = Backtester(strategy, sample_df, initial_capital=10000)
        result = bt.run()
        assert result is not None
        assert result.strategy_name == "SMA Crossover"

    def test_metrics_present(self, sample_df):
        strategy = SMACrossover(fast_period=10, slow_period=30)
        bt = Backtester(strategy, sample_df)
        result = bt.run()
        required_keys = [
            "initial_capital", "final_equity", "total_return",
            "sharpe_ratio", "max_drawdown", "total_trades",
            "win_rate", "profit_factor",
        ]
        for key in required_keys:
            assert key in result.metrics, f"Missing metric: {key}"

    def test_initial_capital_preserved_no_trades(self):
        """With constant price, no crossovers → no trades."""
        n = 100
        df = pd.DataFrame({
            "timestamp": pd.date_range("2025-01-01", periods=n, freq="h"),
            "datetime": pd.date_range("2025-01-01", periods=n, freq="h"),
            "open": [100.0] * n,
            "high": [101.0] * n,
            "low": [99.0] * n,
            "close": [100.0] * n,
            "volume": [5000.0] * n,
        })
        strategy = SMACrossover(fast_period=10, slow_period=30)
        bt = Backtester(strategy, df, initial_capital=10000)
        result = bt.run()
        assert result.metrics["total_trades"] == 0
        assert result.metrics["final_equity"] == 10000.0

    def test_equity_df_not_empty(self, sample_df):
        strategy = SMACrossover()
        bt = Backtester(strategy, sample_df)
        result = bt.run()
        assert not result.equity_df.empty

    def test_summary_string(self, sample_df):
        strategy = SMACrossover()
        bt = Backtester(strategy, sample_df)
        result = bt.run()
        s = result.summary()
        assert "SMA Crossover" in s
        assert "Total Return" in s


class TestCompareStrategies:
    def test_compare_returns_list(self, sample_df):
        strategies = [get_strategy(n) for n in list_strategies()]
        results = compare_strategies(strategies, sample_df)
        assert len(results) == len(list_strategies())

    def test_compare_sorted_by_return(self, sample_df):
        strategies = [get_strategy(n) for n in list_strategies()]
        results = compare_strategies(strategies, sample_df)
        returns = [r.metrics["total_return"] for r in results]
        assert returns == sorted(returns, reverse=True)


class TestPortfolio:
    def test_initial_state(self):
        p = Portfolio(initial_capital=10000)
        assert p.cash == 10000
        assert p.position is None
        assert len(p.trades) == 0

    def test_open_and_close_position(self):
        p = Portfolio(initial_capital=10000, fee_rate=0.001, slippage=0.0)
        ts = pd.Timestamp("2025-01-01")
        p.open_position(ts, 100.0, 1)
        assert p.position is not None
        trade = p.close_position(ts, 110.0)
        assert trade is not None
        assert trade.pnl > 0
        assert p.position is None

    def test_reset(self):
        p = Portfolio(initial_capital=5000)
        ts = pd.Timestamp("2025-01-01")
        p.open_position(ts, 100.0, 1)
        p.close_position(ts, 105.0)
        p.reset()
        assert p.cash == 5000
        assert p.position is None
        assert len(p.trades) == 0
