"""
Technical Indicators
=====================
Compute common technical analysis indicators on OHLCV DataFrames.
Uses the `ta` library under the hood with a clean wrapper API.
"""

import pandas as pd
import numpy as np
import ta


def add_sma(df: pd.DataFrame, column: str = "close", window: int = 20,
            col_name: str = None) -> pd.DataFrame:
    """
    Simple Moving Average.

    Args:
        df: OHLCV DataFrame.
        column: Column to compute SMA on.
        window: Window size.
        col_name: Output column name. Defaults to 'sma_{window}'.
    """
    col_name = col_name or f"sma_{window}"
    df[col_name] = ta.trend.sma_indicator(df[column], window=window)
    return df


def add_ema(df: pd.DataFrame, column: str = "close", window: int = 20,
            col_name: str = None) -> pd.DataFrame:
    """
    Exponential Moving Average.
    """
    col_name = col_name or f"ema_{window}"
    df[col_name] = ta.trend.ema_indicator(df[column], window=window)
    return df


def add_rsi(df: pd.DataFrame, column: str = "close", period: int = 14,
            col_name: str = "rsi") -> pd.DataFrame:
    """
    Relative Strength Index (0–100).
    """
    df[col_name] = ta.momentum.rsi(df[column], window=period)
    return df


def add_macd(df: pd.DataFrame, column: str = "close",
             fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Moving Average Convergence Divergence.
    Adds columns: macd, macd_signal, macd_histogram.
    """
    macd_obj = ta.trend.MACD(df[column], window_fast=fast,
                              window_slow=slow, window_sign=signal)
    df["macd"] = macd_obj.macd()
    df["macd_signal"] = macd_obj.macd_signal()
    df["macd_histogram"] = macd_obj.macd_diff()
    return df


def add_bollinger_bands(df: pd.DataFrame, column: str = "close",
                        window: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """
    Bollinger Bands.
    Adds columns: bb_upper, bb_middle, bb_lower, bb_width, bb_percent.
    """
    bb = ta.volatility.BollingerBands(df[column], window=window,
                                       window_dev=std_dev)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_middle"] = bb.bollinger_mavg()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_width"] = bb.bollinger_wband()
    df["bb_percent"] = bb.bollinger_pband()
    return df


def add_atr(df: pd.DataFrame, period: int = 14,
            col_name: str = "atr") -> pd.DataFrame:
    """
    Average True Range — measures volatility.
    """
    df[col_name] = ta.volatility.average_true_range(
        df["high"], df["low"], df["close"], window=period
    )
    return df


def add_stochastic(df: pd.DataFrame, k_period: int = 14,
                   d_period: int = 3) -> pd.DataFrame:
    """
    Stochastic Oscillator.
    Adds columns: stoch_k, stoch_d.
    """
    stoch = ta.momentum.StochasticOscillator(
        df["high"], df["low"], df["close"],
        window=k_period, smooth_window=d_period
    )
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()
    return df


def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Volume Weighted Average Price.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    df["vwap"] = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
    return df


def add_obv(df: pd.DataFrame) -> pd.DataFrame:
    """
    On Balance Volume.
    """
    df["obv"] = ta.volume.on_balance_volume(df["close"], df["volume"])
    return df


def add_all_indicators(df: pd.DataFrame, config: dict = None) -> pd.DataFrame:
    """
    Add all indicators to the DataFrame with default or config-driven params.

    Args:
        df: OHLCV DataFrame.
        config: Optional dict with strategy params.

    Returns:
        DataFrame with all indicator columns added.
    """
    config = config or {}

    df = add_sma(df, window=config.get("sma_fast", 20), col_name="sma_fast")
    df = add_sma(df, window=config.get("sma_slow", 50), col_name="sma_slow")
    df = add_ema(df, window=20)
    df = add_ema(df, window=50, col_name="ema_50")
    df = add_rsi(df, period=config.get("rsi_period", 14))
    df = add_macd(df,
                  fast=config.get("macd_fast", 12),
                  slow=config.get("macd_slow", 26),
                  signal=config.get("macd_signal", 9))
    df = add_bollinger_bands(df,
                              window=config.get("bb_period", 20),
                              std_dev=config.get("bb_std", 2.0))
    df = add_atr(df, period=config.get("atr_period", 14))
    df = add_stochastic(df,
                         k_period=config.get("stoch_k", 14),
                         d_period=config.get("stoch_d", 3))
    df = add_vwap(df)
    df = add_obv(df)

    return df
