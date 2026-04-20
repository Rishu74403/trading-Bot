"""
Paper Trader
=============
Simulates live trading by polling exchange data at intervals
and executing strategy signals in real-time (without real orders).
"""

import time
from datetime import datetime, timezone

import ccxt
import pandas as pd

from bot.data_fetcher import create_exchange, fetch_ohlcv, fetch_ticker
from bot.strategies import Strategy, get_strategy
from bot.portfolio import Portfolio
from config import load_config, get_strategy_params
from utils.logger import get_logger

logger = get_logger(__name__)


class PaperTrader:
    """
    Paper trading engine — executes a strategy against live market data
    without placing real orders.
    """

    def __init__(self, strategy: Strategy, exchange: ccxt.Exchange,
                 symbol: str = "BTC/USDT", timeframe: str = "1h",
                 initial_capital: float = 10000.0,
                 fee_rate: float = 0.001,
                 update_interval: int = 60):
        self.strategy = strategy
        self.exchange = exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.update_interval = update_interval
        self.running = False

        self.portfolio = Portfolio(
            initial_capital=initial_capital,
            fee_rate=fee_rate,
        )

    def start(self) -> None:
        """Start the paper trading loop."""
        logger.info(f"Starting paper trade: {self.strategy.get_name()} "
                    f"on {self.symbol} {self.timeframe}")
        logger.info(f"Capital: ${self.portfolio.initial_capital:,.2f} | "
                    f"Update interval: {self.update_interval}s")

        self.running = True
        iteration = 0

        try:
            while self.running:
                iteration += 1
                self._tick(iteration)
                logger.info(f"Sleeping {self.update_interval}s until next tick...")
                time.sleep(self.update_interval)
        except KeyboardInterrupt:
            logger.info("Paper trading stopped by user (Ctrl+C)")
            self.stop()

    def stop(self) -> None:
        """Stop the paper trading loop."""
        self.running = False
        # Close any open position
        if self.portfolio.position is not None:
            try:
                ticker = fetch_ticker(self.exchange, self.symbol)
                price = ticker["last"]
                now = datetime.now(timezone.utc)
                self.portfolio.close_position(now, price, "shutdown")
                logger.info(f"Closed position at shutdown: ${price:,.2f}")
            except Exception as e:
                logger.error(f"Error closing position on shutdown: {e}")

        self._print_summary()

    def _tick(self, iteration: int) -> None:
        """Single iteration: fetch data, generate signal, execute."""
        try:
            # Fetch recent candles for indicator calculation
            df = fetch_ohlcv(self.exchange, self.symbol,
                             self.timeframe, limit=200, use_cache=False)

            if df.empty:
                logger.warning("No data returned, skipping tick")
                return

            # Generate signals
            signals_df = self.strategy.generate_signals(df)
            latest = signals_df.iloc[-1]
            signal = latest.get("signal", 0)
            price = latest["close"]
            now = datetime.now(timezone.utc)

            # Log current state
            pos_status = "OPEN" if self.portfolio.position else "FLAT"
            equity = self.portfolio.cash
            if self.portfolio.position:
                equity += self.portfolio.position.quantity * price

            logger.info(
                f"[Tick #{iteration}] {self.symbol} = ${price:,.2f} | "
                f"Signal: {signal:+d} | Position: {pos_status} | "
                f"Equity: ${equity:,.2f}"
            )

            # Execute signal
            if signal == 1 and self.portfolio.position is None:
                opened = self.portfolio.open_position(now, price, signal)
                if opened:
                    qty = self.portfolio.position.quantity
                    logger.info(f"  ► OPENED LONG: {qty:.6f} @ ${price:,.2f}")

            elif signal == -1 and self.portfolio.position is not None:
                trade = self.portfolio.close_position(now, price, "signal")
                if trade:
                    logger.info(f"  ► CLOSED LONG: P&L = ${trade.pnl:,.2f} "
                                f"({trade.return_pct * 100:+.2f}%)")

            # Check stop-loss / take-profit
            if self.portfolio.position:
                trade = self.portfolio.check_stop_loss_take_profit(
                    now, latest["high"], latest["low"])
                if trade:
                    logger.info(f"  ► SL/TP HIT: P&L = ${trade.pnl:,.2f}")

            # Record equity
            self.portfolio.record_equity(now, price)

        except Exception as e:
            logger.error(f"Error in tick #{iteration}: {e}")

    def _print_summary(self) -> None:
        """Print paper trading summary."""
        trades_df = self.portfolio.get_trades_df()
        total_trades = len(trades_df)
        total_pnl = trades_df["pnl"].sum() if total_trades > 0 else 0

        logger.info(f"\n{'═' * 45}")
        logger.info(f"  PAPER TRADING SUMMARY")
        logger.info(f"{'═' * 45}")
        logger.info(f"  Strategy:      {self.strategy.get_name()}")
        logger.info(f"  Symbol:        {self.symbol}")
        logger.info(f"  Total trades:  {total_trades}")
        logger.info(f"  Total P&L:     ${total_pnl:,.2f}")
        logger.info(f"  Final equity:  ${self.portfolio.cash:,.2f}")
        logger.info(f"{'═' * 45}\n")


def run_paper_trading(config: dict = None) -> None:
    """Convenience function to start paper trading from config."""
    if config is None:
        config = load_config()

    exchange = create_exchange(config.get("exchange", "binance"))
    strategy_name = config.get("strategy", "sma_crossover")
    strategy_params = get_strategy_params(config, strategy_name)
    strategy = get_strategy(strategy_name, strategy_params)

    trader = PaperTrader(
        strategy=strategy,
        exchange=exchange,
        symbol=config.get("trading_pair", "BTC/USDT"),
        timeframe=config.get("timeframe", "1h"),
        initial_capital=config.get("initial_capital", 10000.0),
        fee_rate=config.get("fee_rate", 0.001),
        update_interval=config.get("paper_trade", {}).get("update_interval", 60),
    )
    trader.start()
