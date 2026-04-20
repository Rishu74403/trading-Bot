"""
Plotting Utilities
===================
Matplotlib-based visualization for backtest results.
Generates equity curves, price charts with signals, drawdown, and more.
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server use
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)

CHARTS_DIR = Path(__file__).parent.parent / "charts"

# ── Style ───────────────────────────────────────────────────────────────

COLORS = {
    "bg": "#0d1117",
    "panel": "#161b22",
    "text": "#c9d1d9",
    "grid": "#21262d",
    "green": "#3fb950",
    "red": "#f85149",
    "blue": "#58a6ff",
    "purple": "#bc8cff",
    "orange": "#d29922",
    "cyan": "#39d2c0",
}


def _apply_style(fig, axes):
    """Apply dark theme to figure and axes."""
    fig.patch.set_facecolor(COLORS["bg"])
    if not isinstance(axes, np.ndarray):
        axes = [axes]
    for ax in axes:
        ax.set_facecolor(COLORS["panel"])
        ax.tick_params(colors=COLORS["text"], labelsize=9)
        ax.xaxis.label.set_color(COLORS["text"])
        ax.yaxis.label.set_color(COLORS["text"])
        ax.title.set_color(COLORS["text"])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(COLORS["grid"])
        ax.spines["left"].set_color(COLORS["grid"])
        ax.grid(True, color=COLORS["grid"], alpha=0.5, linewidth=0.5)


def plot_equity_curve(equity_df: pd.DataFrame, title: str = "Equity Curve",
                      save: bool = True) -> str | None:
    """Plot portfolio equity over time."""
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 5))
    _apply_style(fig, ax)

    ax.plot(equity_df["timestamp"], equity_df["equity"],
            color=COLORS["cyan"], linewidth=1.5, label="Equity")
    ax.fill_between(equity_df["timestamp"], equity_df["equity"],
                    alpha=0.1, color=COLORS["cyan"])
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Time")
    ax.set_ylabel("Portfolio Value ($)")
    ax.legend(facecolor=COLORS["panel"], edgecolor=COLORS["grid"],
              labelcolor=COLORS["text"])

    plt.tight_layout()
    path = None
    if save:
        path = str(CHARTS_DIR / "equity_curve.png")
        fig.savefig(path, dpi=150, facecolor=COLORS["bg"])
        logger.info(f"Saved equity curve: {path}")
    plt.close(fig)
    return path


def plot_price_with_signals(signals_df: pd.DataFrame,
                            title: str = "Price & Signals",
                            save: bool = True) -> str | None:
    """Plot price chart with buy/sell markers."""
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 6))
    _apply_style(fig, ax)

    ts = signals_df.get("datetime", signals_df.get("timestamp"))
    ax.plot(ts, signals_df["close"], color=COLORS["blue"],
            linewidth=1, alpha=0.9, label="Close Price")

    buys = signals_df[signals_df["signal"] == 1]
    sells = signals_df[signals_df["signal"] == -1]

    buy_ts = buys.get("datetime", buys.get("timestamp"))
    sell_ts = sells.get("datetime", sells.get("timestamp"))

    ax.scatter(buy_ts, buys["close"], marker="^", color=COLORS["green"],
               s=80, zorder=5, label=f"Buy ({len(buys)})", edgecolors="white",
               linewidths=0.5)
    ax.scatter(sell_ts, sells["close"], marker="v", color=COLORS["red"],
               s=80, zorder=5, label=f"Sell ({len(sells)})", edgecolors="white",
               linewidths=0.5)

    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Time")
    ax.set_ylabel("Price ($)")
    ax.legend(facecolor=COLORS["panel"], edgecolor=COLORS["grid"],
              labelcolor=COLORS["text"])

    plt.tight_layout()
    path = None
    if save:
        path = str(CHARTS_DIR / "price_signals.png")
        fig.savefig(path, dpi=150, facecolor=COLORS["bg"])
        logger.info(f"Saved price chart: {path}")
    plt.close(fig)
    return path


def plot_drawdown(equity_df: pd.DataFrame, title: str = "Drawdown",
                  save: bool = True) -> str | None:
    """Plot drawdown chart."""
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    equity = equity_df["equity"]
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax * 100

    fig, ax = plt.subplots(figsize=(14, 4))
    _apply_style(fig, ax)

    ax.fill_between(equity_df["timestamp"], drawdown, 0,
                    color=COLORS["red"], alpha=0.4)
    ax.plot(equity_df["timestamp"], drawdown, color=COLORS["red"],
            linewidth=1)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Time")
    ax.set_ylabel("Drawdown (%)")

    plt.tight_layout()
    path = None
    if save:
        path = str(CHARTS_DIR / "drawdown.png")
        fig.savefig(path, dpi=150, facecolor=COLORS["bg"])
        logger.info(f"Saved drawdown chart: {path}")
    plt.close(fig)
    return path


def plot_returns_distribution(trades_df: pd.DataFrame,
                              title: str = "Trade Returns Distribution",
                              save: bool = True) -> str | None:
    """Plot histogram of trade returns."""
    if trades_df.empty:
        return None

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    _apply_style(fig, ax)

    returns = trades_df["return_pct"] * 100
    colors = [COLORS["green"] if r > 0 else COLORS["red"] for r in returns]

    ax.hist(returns, bins=30, color=COLORS["blue"], alpha=0.7,
            edgecolor=COLORS["panel"])
    ax.axvline(x=0, color=COLORS["text"], linestyle="--", alpha=0.5)
    ax.axvline(x=returns.mean(), color=COLORS["orange"], linestyle="-",
               alpha=0.8, label=f"Mean: {returns.mean():.2f}%")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Return (%)")
    ax.set_ylabel("Frequency")
    ax.legend(facecolor=COLORS["panel"], edgecolor=COLORS["grid"],
              labelcolor=COLORS["text"])

    plt.tight_layout()
    path = None
    if save:
        path = str(CHARTS_DIR / "returns_dist.png")
        fig.savefig(path, dpi=150, facecolor=COLORS["bg"])
        logger.info(f"Saved returns distribution: {path}")
    plt.close(fig)
    return path


def plot_all(result, save: bool = True) -> list[str]:
    """Generate all charts for a BacktestResult. Returns list of file paths."""
    paths = []
    title_prefix = f"{result.strategy_name} — {result.symbol}"

    p = plot_equity_curve(result.equity_df,
                          f"{title_prefix} Equity Curve", save)
    if p:
        paths.append(p)

    p = plot_price_with_signals(result.signals_df,
                                f"{title_prefix} Signals", save)
    if p:
        paths.append(p)

    p = plot_drawdown(result.equity_df,
                      f"{title_prefix} Drawdown", save)
    if p:
        paths.append(p)

    p = plot_returns_distribution(result.trades_df,
                                  f"{title_prefix} Returns", save)
    if p:
        paths.append(p)

    return paths
