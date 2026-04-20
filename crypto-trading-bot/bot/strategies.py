"""
Trading Strategies
===================
Base strategy class and four built-in strategies:
  1. SMA Crossover
  2. RSI Mean Reversion
  3. MACD Signal
  4. Bollinger Bands Breakout
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

from bot.indicators import (
    add_sma, add_rsi, add_macd, add_bollinger_bands
)
from utils.logger import get_logger

logger = get_logger(__name__)


class Strategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, params: dict = None):
        self.params = params or {}

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add 'signal' column: 1=BUY, -1=SELL, 0=HOLD."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        ...

    def get_params(self) -> dict:
        return self.params.copy()

    def __repr__(self) -> str:
        return f"{self.get_name()}({self.params})"


class SMACrossover(Strategy):
    """BUY on golden cross, SELL on death cross."""

    def __init__(self, fast_period: int = 20, slow_period: int = 50, **kw):
        super().__init__({"fast_period": fast_period, "slow_period": slow_period})
        self.fast = fast_period
        self.slow = slow_period

    def get_name(self) -> str:
        return "SMA Crossover"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = add_sma(df, window=self.fast, col_name="sma_fast")
        df = add_sma(df, window=self.slow, col_name="sma_slow")
        df["signal"] = 0
        up = (df["sma_fast"] > df["sma_slow"]) & (df["sma_fast"].shift(1) <= df["sma_slow"].shift(1))
        dn = (df["sma_fast"] < df["sma_slow"]) & (df["sma_fast"].shift(1) >= df["sma_slow"].shift(1))
        df.loc[up, "signal"] = 1
        df.loc[dn, "signal"] = -1
        logger.debug(f"SMA Crossover: {up.sum()} buys, {dn.sum()} sells")
        return df


class RSIMeanReversion(Strategy):
    """BUY when oversold, SELL when overbought."""

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70, **kw):
        super().__init__({"period": period, "oversold": oversold, "overbought": overbought})
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def get_name(self) -> str:
        return "RSI Mean Reversion"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = add_rsi(df, period=self.period)
        df["signal"] = 0
        buy = (df["rsi"] < self.oversold) & (df["rsi"].shift(1) >= self.oversold)
        sell = (df["rsi"] > self.overbought) & (df["rsi"].shift(1) <= self.overbought)
        df.loc[buy, "signal"] = 1
        df.loc[sell, "signal"] = -1
        logger.debug(f"RSI: {buy.sum()} buys, {sell.sum()} sells")
        return df


class MACDSignal(Strategy):
    """BUY/SELL on MACD-signal line crossover."""

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9, **kw):
        super().__init__({"fast_period": fast_period, "slow_period": slow_period, "signal_period": signal_period})
        self.fast = fast_period
        self.slow = slow_period
        self.signal_period = signal_period

    def get_name(self) -> str:
        return "MACD Signal"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = add_macd(df, fast=self.fast, slow=self.slow, signal=self.signal_period)
        df["signal"] = 0
        up = (df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1))
        dn = (df["macd"] < df["macd_signal"]) & (df["macd"].shift(1) >= df["macd_signal"].shift(1))
        df.loc[up, "signal"] = 1
        df.loc[dn, "signal"] = -1
        logger.debug(f"MACD: {up.sum()} buys, {dn.sum()} sells")
        return df


class BollingerBandsBreakout(Strategy):
    """BUY at lower band, SELL at upper band."""

    def __init__(self, period: int = 20, std_dev: float = 2.0, **kw):
        super().__init__({"period": period, "std_dev": std_dev})
        self.period = period
        self.std_dev = std_dev

    def get_name(self) -> str:
        return "Bollinger Bands Breakout"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = add_bollinger_bands(df, window=self.period, std_dev=self.std_dev)
        df["signal"] = 0
        buy = (df["close"] <= df["bb_lower"]) & (df["close"].shift(1) > df["bb_lower"].shift(1))
        sell = (df["close"] >= df["bb_upper"]) & (df["close"].shift(1) < df["bb_upper"].shift(1))
        df.loc[buy, "signal"] = 1
        df.loc[sell, "signal"] = -1
        logger.debug(f"Bollinger: {buy.sum()} buys, {sell.sum()} sells")
        return df


STRATEGY_MAP = {
    "sma_crossover": SMACrossover,
    "rsi": RSIMeanReversion,
    "macd": MACDSignal,
    "bollinger_bands": BollingerBandsBreakout,
}


def get_strategy(name: str, params: dict = None) -> Strategy:
    """Instantiate a strategy by name."""
    cls = STRATEGY_MAP.get(name)
    if cls is None:
        available = ", ".join(STRATEGY_MAP.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
    return cls(**(params or {}))


def list_strategies() -> list[str]:
    """Return all available strategy names."""
    return list(STRATEGY_MAP.keys())
