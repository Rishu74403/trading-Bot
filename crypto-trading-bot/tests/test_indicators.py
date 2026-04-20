"""Tests for technical indicators."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np

from bot.indicators import (
    add_sma, add_ema, add_rsi, add_macd,
    add_bollinger_bands, add_atr, add_stochastic,
    add_vwap, add_obv, add_all_indicators,
)


@pytest.fixture
def sample_df():
    """Create a sample OHLCV DataFrame for testing."""
    np.random.seed(42)
    n = 100
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="h"),
        "open": close + np.random.randn(n) * 0.5,
        "high": close + abs(np.random.randn(n)) * 2,
        "low": close - abs(np.random.randn(n)) * 2,
        "close": close,
        "volume": np.random.randint(1000, 10000, n).astype(float),
    })


class TestSMA:
    def test_sma_adds_column(self, sample_df):
        df = add_sma(sample_df, window=10)
        assert "sma_10" in df.columns

    def test_sma_custom_name(self, sample_df):
        df = add_sma(sample_df, window=20, col_name="my_sma")
        assert "my_sma" in df.columns

    def test_sma_values_correct(self, sample_df):
        df = add_sma(sample_df, window=5)
        # First 4 values should be NaN
        assert df["sma_5"].iloc[:4].isna().all()
        # 5th value should be mean of first 5 closes
        expected = sample_df["close"].iloc[:5].mean()
        assert abs(df["sma_5"].iloc[4] - expected) < 0.01


class TestEMA:
    def test_ema_adds_column(self, sample_df):
        df = add_ema(sample_df, window=10)
        assert "ema_10" in df.columns


class TestRSI:
    def test_rsi_adds_column(self, sample_df):
        df = add_rsi(sample_df)
        assert "rsi" in df.columns

    def test_rsi_range(self, sample_df):
        df = add_rsi(sample_df)
        valid = df["rsi"].dropna()
        assert (valid >= 0).all() and (valid <= 100).all()


class TestMACD:
    def test_macd_adds_columns(self, sample_df):
        df = add_macd(sample_df)
        assert "macd" in df.columns
        assert "macd_signal" in df.columns
        assert "macd_histogram" in df.columns


class TestBollingerBands:
    def test_bb_adds_columns(self, sample_df):
        df = add_bollinger_bands(sample_df)
        assert "bb_upper" in df.columns
        assert "bb_middle" in df.columns
        assert "bb_lower" in df.columns

    def test_bb_upper_above_lower(self, sample_df):
        df = add_bollinger_bands(sample_df)
        valid = df.dropna(subset=["bb_upper", "bb_lower"])
        assert (valid["bb_upper"] >= valid["bb_lower"]).all()


class TestATR:
    def test_atr_adds_column(self, sample_df):
        df = add_atr(sample_df)
        assert "atr" in df.columns

    def test_atr_positive(self, sample_df):
        df = add_atr(sample_df)
        valid = df["atr"].dropna()
        assert (valid >= 0).all()


class TestStochastic:
    def test_stoch_adds_columns(self, sample_df):
        df = add_stochastic(sample_df)
        assert "stoch_k" in df.columns
        assert "stoch_d" in df.columns


class TestVWAP:
    def test_vwap_adds_column(self, sample_df):
        df = add_vwap(sample_df)
        assert "vwap" in df.columns


class TestOBV:
    def test_obv_adds_column(self, sample_df):
        df = add_obv(sample_df)
        assert "obv" in df.columns


class TestAllIndicators:
    def test_adds_multiple_columns(self, sample_df):
        df = add_all_indicators(sample_df)
        expected = ["sma_fast", "sma_slow", "rsi", "macd", "bb_upper",
                     "atr", "stoch_k", "vwap", "obv"]
        for col in expected:
            assert col in df.columns, f"Missing column: {col}"
