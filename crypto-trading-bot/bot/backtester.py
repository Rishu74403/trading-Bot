"""
Backtesting Engine
===================
Simulates strategy execution on historical data and computes
performance metrics (Sharpe, drawdown, win rate, etc.).
"""

import numpy as np
import pandas as pd
from datetime import datetime

from bot.strategies import Strategy
from bot.portfolio import Portfolio
from utils.logger import get_logger

logger = get_logger(__name__)


class BacktestResult:
    """Container for backtest output."""

    def __init__(self, strategy_name: str, symbol: str, timeframe: str,
                 metrics: dict, equity_df: pd.DataFrame,
                 trades_df: pd.DataFrame, signals_df: pd.DataFrame):
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.timeframe = timeframe
        self.metrics = metrics
        self.equity_df = equity_df
        self.trades_df = trades_df
        self.signals_df = signals_df

    def summary(self) -> str:
        lines = [
            f"\n{'═' * 55}",
            f"  BACKTEST RESULTS — {self.strategy_name}",
            f"  {self.symbol} | {self.timeframe}",
            f"{'═' * 55}",
        ]
        for key, val in self.metrics.items():
            label = key.replace("_", " ").title()
            if isinstance(val, float):
                if "pct" in key or "return" in key or "drawdown" in key or "rate" in key:
                    lines.append(f"  {label:<28} {val:>10.2f}%")
                else:
                    lines.append(f"  {label:<28} {val:>10.2f}")
            else:
                lines.append(f"  {label:<28} {val:>10}")
        lines.append(f"{'═' * 55}\n")
        return "\n".join(lines)


class Backtester:
    """
    Run a strategy against historical OHLCV data.

    Usage:
        bt = Backtester(strategy, df, initial_capital=10000)
        result = bt.run()
        print(result.summary())
    """

    def __init__(self, strategy: Strategy, df: pd.DataFrame,
                 initial_capital: float = 10000.0,
                 fee_rate: float = 0.001,
                 slippage: float = 0.0005,
                 risk_per_trade: float = 0.02,
                 stop_loss: float = 0.05,
                 take_profit: float = 0.10,
                 symbol: str = "BTC/USDT",
                 timeframe: str = "1h"):
        self.strategy = strategy
        self.df = df.copy()
        self.symbol = symbol
        self.timeframe = timeframe

        self.portfolio = Portfolio(
            initial_capital=initial_capital,
            fee_rate=fee_rate,
            slippage=slippage,
            risk_per_trade=risk_per_trade,
            stop_loss_pct=stop_loss,
            take_profit_pct=take_profit,
        )

    def run(self) -> BacktestResult:
        """Execute the backtest and return results."""
        logger.info(f"Running backtest: {self.strategy.get_name()} on "
                    f"{self.symbol} {self.timeframe}")

        # Generate signals
        signals_df = self.strategy.generate_signals(self.df)

        # Iterate through each candle
        for i, row in signals_df.iterrows():
            ts = row.get("datetime", row.get("timestamp"))
            price = row["close"]
            high = row["high"]
            low = row["low"]
            signal = row.get("signal", 0)

            # Check stop-loss / take-profit first
            self.portfolio.check_stop_loss_take_profit(ts, high, low)

            # Process signal
            if signal == 1 and self.portfolio.position is None:
                self.portfolio.open_position(ts, price, signal)
            elif signal == -1 and self.portfolio.position is not None:
                self.portfolio.close_position(ts, price, "signal")

            # Record equity
            self.portfolio.record_equity(ts, price)

        # Close any remaining position at the last price
        if self.portfolio.position is not None:
            last = signals_df.iloc[-1]
            ts = last.get("datetime", last.get("timestamp"))
            self.portfolio.close_position(ts, last["close"], "end_of_data")

        # Compute metrics
        equity_df = self.portfolio.get_equity_df()
        trades_df = self.portfolio.get_trades_df()
        metrics = self._compute_metrics(equity_df, trades_df)

        result = BacktestResult(
            strategy_name=self.strategy.get_name(),
            symbol=self.symbol,
            timeframe=self.timeframe,
            metrics=metrics,
            equity_df=equity_df,
            trades_df=trades_df,
            signals_df=signals_df,
        )

        logger.info(f"Backtest complete: {metrics.get('total_trades', 0)} trades")
        return result

    def _compute_metrics(self, equity_df: pd.DataFrame,
                         trades_df: pd.DataFrame) -> dict:
        """Calculate performance metrics."""
        initial = self.portfolio.initial_capital

        if equity_df.empty:
            return self._empty_metrics(initial)

        final_equity = equity_df["equity"].iloc[-1]
        total_return = ((final_equity - initial) / initial) * 100

        # Returns series
        equity_series = equity_df["equity"]
        returns = equity_series.pct_change().dropna()

        # Sharpe ratio (annualized, assuming hourly data → 8760 periods/year)
        tf_map = {"1m": 525600, "5m": 105120, "15m": 35040,
                  "1h": 8760, "4h": 2190, "1d": 365}
        periods_year = tf_map.get(self.timeframe, 8760)

        sharpe = 0.0
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(periods_year)

        # Max drawdown
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax
        max_drawdown = drawdown.min() * 100

        # Trade statistics
        total_trades = len(trades_df)
        winning = 0
        losing = 0
        gross_profit = 0.0
        gross_loss = 0.0
        total_fees = 0.0

        if total_trades > 0:
            winning = len(trades_df[trades_df["pnl"] > 0])
            losing = len(trades_df[trades_df["pnl"] <= 0])
            gross_profit = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
            gross_loss = abs(trades_df[trades_df["pnl"] <= 0]["pnl"].sum())
            total_fees = trades_df["fee"].sum()

        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
        avg_trade_return = trades_df["return_pct"].mean() * 100 if total_trades > 0 else 0.0

        return {
            "initial_capital": initial,
            "final_equity": round(final_equity, 2),
            "total_return": round(total_return, 2),
            "sharpe_ratio": round(sharpe, 3),
            "max_drawdown": round(max_drawdown, 2),
            "total_trades": total_trades,
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 3),
            "avg_trade_return": round(avg_trade_return, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "total_fees": round(total_fees, 2),
        }

    @staticmethod
    def _empty_metrics(initial: float) -> dict:
        return {
            "initial_capital": initial,
            "final_equity": initial,
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_trade_return": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "total_fees": 0.0,
        }


def compare_strategies(strategies: list[Strategy], df: pd.DataFrame,
                       **kwargs) -> list[BacktestResult]:
    """Run multiple strategies on the same data and return sorted results."""
    results = []
    for strat in strategies:
        bt = Backtester(strat, df, **kwargs)
        results.append(bt.run())
    results.sort(key=lambda r: r.metrics.get("total_return", 0), reverse=True)
    return results
