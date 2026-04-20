"""
Portfolio Manager
==================
Tracks positions, trade history, and portfolio value over time.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import pandas as pd


@dataclass
class Trade:
    """A single completed trade."""
    entry_time: datetime
    exit_time: datetime
    side: str           # 'long'
    entry_price: float
    exit_price: float
    quantity: float
    fee: float
    pnl: float          # net P&L after fees
    return_pct: float   # percentage return


@dataclass
class Position:
    """An open position."""
    entry_time: datetime
    side: str
    entry_price: float
    quantity: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class Portfolio:
    """
    Manages capital, positions, and trade history.
    """

    def __init__(self, initial_capital: float = 10000.0,
                 fee_rate: float = 0.001,
                 slippage: float = 0.0005,
                 risk_per_trade: float = 0.02,
                 stop_loss_pct: float = 0.05,
                 take_profit_pct: float = 0.10):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.risk_per_trade = risk_per_trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

        self.position: Optional[Position] = None
        self.trades: list[Trade] = []
        self.equity_curve: list[dict] = []

    @property
    def total_value(self) -> float:
        """Current portfolio value (cash + open position value)."""
        return self.cash

    def calculate_position_size(self, price: float) -> float:
        """Position size based on risk-per-trade."""
        risk_amount = self.cash * self.risk_per_trade
        quantity = risk_amount / (price * self.stop_loss_pct)
        max_quantity = (self.cash * 0.95) / price  # max 95% of cash
        return min(quantity, max_quantity)

    def open_position(self, timestamp: datetime, price: float,
                      signal: int) -> bool:
        """Open a new position. Returns True if opened."""
        if self.position is not None:
            return False

        slipped_price = price * (1 + self.slippage) if signal == 1 else price * (1 - self.slippage)
        quantity = self.calculate_position_size(slipped_price)

        if quantity <= 0:
            return False

        cost = quantity * slipped_price
        fee = cost * self.fee_rate

        if cost + fee > self.cash:
            quantity = (self.cash * 0.95) / (slipped_price * (1 + self.fee_rate))
            cost = quantity * slipped_price
            fee = cost * self.fee_rate

        self.cash -= (cost + fee)

        self.position = Position(
            entry_time=timestamp,
            side="long",
            entry_price=slipped_price,
            quantity=quantity,
            stop_loss=slipped_price * (1 - self.stop_loss_pct),
            take_profit=slipped_price * (1 + self.take_profit_pct),
        )
        return True

    def close_position(self, timestamp: datetime, price: float,
                       reason: str = "signal") -> Optional[Trade]:
        """Close the current position. Returns the Trade or None."""
        if self.position is None:
            return None

        slipped_price = price * (1 - self.slippage)
        revenue = self.position.quantity * slipped_price
        fee = revenue * self.fee_rate
        net_revenue = revenue - fee

        entry_cost = self.position.quantity * self.position.entry_price
        pnl = net_revenue - entry_cost
        return_pct = pnl / entry_cost if entry_cost > 0 else 0.0

        trade = Trade(
            entry_time=self.position.entry_time,
            exit_time=timestamp,
            side=self.position.side,
            entry_price=self.position.entry_price,
            exit_price=slipped_price,
            quantity=self.position.quantity,
            fee=fee + (entry_cost * self.fee_rate),
            pnl=pnl,
            return_pct=return_pct,
        )
        self.trades.append(trade)
        self.cash += net_revenue
        self.position = None
        return trade

    def check_stop_loss_take_profit(self, timestamp: datetime,
                                     high: float, low: float) -> Optional[Trade]:
        """Check if SL/TP was hit. Returns Trade if position closed."""
        if self.position is None:
            return None

        if self.position.stop_loss and low <= self.position.stop_loss:
            return self.close_position(timestamp, self.position.stop_loss, "stop_loss")

        if self.position.take_profit and high >= self.position.take_profit:
            return self.close_position(timestamp, self.position.take_profit, "take_profit")

        return None

    def record_equity(self, timestamp: datetime, price: float) -> None:
        """Snapshot current portfolio value."""
        pos_value = 0.0
        if self.position:
            pos_value = self.position.quantity * price
        total = self.cash + pos_value
        self.equity_curve.append({
            "timestamp": timestamp,
            "equity": total,
            "cash": self.cash,
            "position_value": pos_value,
        })

    def get_equity_df(self) -> pd.DataFrame:
        """Return equity curve as DataFrame."""
        if not self.equity_curve:
            return pd.DataFrame(columns=["timestamp", "equity", "cash", "position_value"])
        return pd.DataFrame(self.equity_curve)

    def get_trades_df(self) -> pd.DataFrame:
        """Return trade history as DataFrame."""
        if not self.trades:
            return pd.DataFrame()
        records = []
        for t in self.trades:
            records.append({
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "side": t.side,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "quantity": t.quantity,
                "fee": t.fee,
                "pnl": t.pnl,
                "return_pct": t.return_pct,
            })
        return pd.DataFrame(records)

    def reset(self) -> None:
        """Reset portfolio to initial state."""
        self.cash = self.initial_capital
        self.position = None
        self.trades.clear()
        self.equity_curve.clear()
