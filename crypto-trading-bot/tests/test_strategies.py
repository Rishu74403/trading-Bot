"""Tests for trading strategies."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np

from bot.strategies import (
    SMACrossover, RSIMeanReversion, MACDSignal,
    BollingerBandsBreakout, get_strategy, list_strategies,
)


@pytest.fixture
def sample_df():
    np.random.seed(42)
    n = 200
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="h"),
        "open": close + np.random.randn(n) * 0.5,
        "high": close + abs(np.random.randn(n)) * 2,
        "low": close - abs(np.random.randn(n)) * 2,
        "close": close,
        "volume": np.random.randint(1000, 10000, n).astype(float),
    })


class TestSMACrossover:
    def test_generates_signal_column(self, sample_df):
        s = SMACrossover(fast_period=10, slow_period=30)
        df = s.generate_signals(sample_df)
        assert "signal" in df.columns

    def test_signals_valid_values(self, sample_df):
        s = SMACrossover()
        df = s.generate_signals(sample_df)
        assert set(df["signal"].unique()).issubset({-1, 0, 1})

    def test_name(self):
        assert SMACrossover().get_name() == "SMA Crossover"


class TestRSI:
    def test_generates_signals(self, sample_df):
        s = RSIMeanReversion()
        df = s.generate_signals(sample_df)
        assert "signal" in df.columns
        assert set(df["signal"].unique()).issubset({-1, 0, 1})


class TestMACD:
    def test_generates_signals(self, sample_df):
        s = MACDSignal()
        df = s.generate_signals(sample_df)
        assert "signal" in df.columns
        assert set(df["signal"].unique()).issubset({-1, 0, 1})


class TestBollingerBands:
    def test_generates_signals(self, sample_df):
        s = BollingerBandsBreakout()
        df = s.generate_signals(sample_df)
        assert "signal" in df.columns
        assert set(df["signal"].unique()).issubset({-1, 0, 1})


class TestStrategyRegistry:
    def test_get_strategy(self):
        s = get_strategy("sma_crossover")
        assert s.get_name() == "SMA Crossover"

    def test_get_strategy_with_params(self):
        s = get_strategy("rsi", {"period": 20, "oversold": 25, "overbought": 75})
        assert s.params["period"] == 20

    def test_invalid_strategy(self):
        with pytest.raises(ValueError):
            get_strategy("nonexistent")

    def test_list_strategies(self):
        names = list_strategies()
        assert "sma_crossover" in names
        assert "rsi" in names
        assert "macd" in names
        assert "bollinger_bands" in names
