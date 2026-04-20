#!/usr/bin/env python3
"""
Crypto Trading Bot — CLI Entry Point
======================================
Usage:
    python main.py backtest --strategy sma_crossover --pair BTC/USDT
    python main.py paper-trade --strategy rsi --pair ETH/USDT
    python main.py data --pair BTC/USDT --timeframe 4h --limit 50
    python main.py compare --pair BTC/USDT --timeframe 1h
    python main.py strategies
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from config import load_config, get_strategy_params
from bot.data_fetcher import create_exchange, fetch_ohlcv, fetch_ticker
from bot.strategies import get_strategy, list_strategies, STRATEGY_MAP
from bot.backtester import Backtester, compare_strategies
from bot.trader import run_paper_trading
from utils.plotting import plot_all
from utils.logger import get_logger

console = Console()
logger = get_logger(__name__)

BANNER = r"""
[cyan]
   ██████╗██████╗ ██╗   ██╗██████╗ ████████╗ ██████╗     ██████╗  ██████╗ ████████╗
  ██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗    ██╔══██╗██╔═══██╗╚══██╔══╝
  ██║     ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║   ██║    ██████╔╝██║   ██║   ██║
  ██║     ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║   ██║    ██╔══██╗██║   ██║   ██║
  ╚██████╗██║  ██║   ██║   ██║        ██║   ╚██████╔╝    ██████╔╝╚██████╔╝   ██║
   ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝    ╚═════╝     ╚═════╝  ╚═════╝    ╚═╝
[/cyan]
[dim]  Cryptocurrency Trading Bot v1.0.0 — CCXT Powered[/dim]
"""


def cmd_backtest(args, config):
    """Run a backtest on historical data."""
    console.print(BANNER)
    console.print(Panel(f"[bold cyan]Backtesting: {args.strategy}[/bold cyan] on "
                        f"[yellow]{args.pair}[/yellow] ({args.timeframe})",
                        box=box.DOUBLE))

    exchange = create_exchange(config.get("exchange", "binance"))
    strategy_params = get_strategy_params(config, args.strategy)
    strategy = get_strategy(args.strategy, strategy_params)

    console.print(f"\n[dim]Fetching historical data...[/dim]")
    df = fetch_ohlcv(exchange, args.pair, args.timeframe,
                     since=args.start, limit=args.limit)

    if df.empty:
        console.print("[red]No data returned. Check the trading pair and exchange.[/red]")
        return

    console.print(f"[green]✓[/green] Loaded {len(df)} candles")

    bt = Backtester(
        strategy=strategy, df=df,
        initial_capital=config.get("initial_capital", 10000),
        fee_rate=config.get("fee_rate", 0.001),
        slippage=config.get("slippage", 0.0005),
        risk_per_trade=config.get("risk_per_trade", 0.02),
        stop_loss=config.get("stop_loss", 0.05),
        take_profit=config.get("take_profit", 0.10),
        symbol=args.pair, timeframe=args.timeframe,
    )

    result = bt.run()

    # Display metrics table
    table = Table(title="Performance Metrics", box=box.ROUNDED,
                  title_style="bold cyan", border_style="dim")
    table.add_column("Metric", style="white", min_width=25)
    table.add_column("Value", style="cyan", justify="right", min_width=15)

    for key, val in result.metrics.items():
        label = key.replace("_", " ").title()
        if isinstance(val, float):
            if any(k in key for k in ["return", "drawdown", "rate"]):
                color = "green" if val >= 0 else "red"
                table.add_row(label, f"[{color}]{val:.2f}%[/{color}]")
            else:
                table.add_row(label, f"{val:,.2f}")
        else:
            table.add_row(label, str(val))

    console.print(table)

    # Generate charts
    if not args.no_charts:
        console.print(f"\n[dim]Generating charts...[/dim]")
        paths = plot_all(result)
        for p in paths:
            console.print(f"[green]✓[/green] Saved: {p}")

    # Trade log
    if not result.trades_df.empty and args.show_trades:
        trades_table = Table(title="Trade Log", box=box.SIMPLE,
                             title_style="bold yellow")
        trades_table.add_column("#", style="dim")
        trades_table.add_column("Entry", style="white")
        trades_table.add_column("Exit", style="white")
        trades_table.add_column("Entry $", justify="right")
        trades_table.add_column("Exit $", justify="right")
        trades_table.add_column("P&L", justify="right")
        trades_table.add_column("Return", justify="right")

        for i, row in result.trades_df.iterrows():
            pnl_color = "green" if row["pnl"] > 0 else "red"
            trades_table.add_row(
                str(i + 1),
                str(row["entry_time"])[:19],
                str(row["exit_time"])[:19],
                f"${row['entry_price']:,.2f}",
                f"${row['exit_price']:,.2f}",
                f"[{pnl_color}]${row['pnl']:,.2f}[/{pnl_color}]",
                f"[{pnl_color}]{row['return_pct'] * 100:+.2f}%[/{pnl_color}]",
            )

        console.print(trades_table)


def cmd_paper_trade(args, config):
    """Start paper trading."""
    console.print(BANNER)
    console.print(Panel("[bold green]Paper Trading Mode[/bold green]\n"
                        "Press Ctrl+C to stop", box=box.DOUBLE))

    config["strategy"] = args.strategy
    config["trading_pair"] = args.pair
    config["timeframe"] = args.timeframe
    run_paper_trading(config)


def cmd_data(args, config):
    """Fetch and display market data."""
    console.print(BANNER)
    exchange = create_exchange(config.get("exchange", "binance"))

    # Current ticker
    console.print(f"\n[bold]Current Ticker — {args.pair}[/bold]")
    try:
        ticker = fetch_ticker(exchange, args.pair)
        ticker_table = Table(box=box.SIMPLE_HEAVY, border_style="cyan")
        ticker_table.add_column("Field", style="dim")
        ticker_table.add_column("Value", style="cyan bold")
        for k, v in ticker.items():
            if v is not None:
                ticker_table.add_row(k.title(), f"{v:,.6f}" if isinstance(v, float) else str(v))
        console.print(ticker_table)
    except Exception as e:
        console.print(f"[red]Ticker error: {e}[/red]")

    # OHLCV data
    console.print(f"\n[bold]Recent OHLCV — {args.pair} ({args.timeframe})[/bold]")
    df = fetch_ohlcv(exchange, args.pair, args.timeframe, limit=args.limit)
    if not df.empty:
        display = df[["datetime", "open", "high", "low", "close", "volume"]].tail(20)
        table = Table(box=box.SIMPLE, border_style="dim")
        for col in display.columns:
            table.add_column(col.title(), justify="right" if col != "datetime" else "left")
        for _, row in display.iterrows():
            table.add_row(
                str(row["datetime"])[:19],
                f"{row['open']:,.2f}",
                f"{row['high']:,.2f}",
                f"{row['low']:,.2f}",
                f"{row['close']:,.2f}",
                f"{row['volume']:,.2f}",
            )
        console.print(table)
        console.print(f"[dim]Showing last 20 of {len(df)} candles[/dim]")


def cmd_compare(args, config):
    """Compare all strategies on the same data."""
    console.print(BANNER)
    console.print(Panel("[bold purple]Strategy Comparison[/bold purple]", box=box.DOUBLE))

    exchange = create_exchange(config.get("exchange", "binance"))
    console.print(f"[dim]Fetching data for {args.pair}...[/dim]")
    df = fetch_ohlcv(exchange, args.pair, args.timeframe,
                     since=args.start, limit=args.limit)

    if df.empty:
        console.print("[red]No data returned.[/red]")
        return

    console.print(f"[green]✓[/green] Loaded {len(df)} candles\n")

    strategies = []
    for name in list_strategies():
        params = get_strategy_params(config, name)
        strategies.append(get_strategy(name, params))

    results = compare_strategies(
        strategies, df,
        initial_capital=config.get("initial_capital", 10000),
        fee_rate=config.get("fee_rate", 0.001),
        symbol=args.pair, timeframe=args.timeframe,
    )

    table = Table(title="Strategy Comparison", box=box.ROUNDED,
                  title_style="bold purple", border_style="dim")
    table.add_column("Rank", style="bold", justify="center")
    table.add_column("Strategy", style="white")
    table.add_column("Return", justify="right")
    table.add_column("Sharpe", justify="right")
    table.add_column("Max DD", justify="right")
    table.add_column("Trades", justify="right")
    table.add_column("Win Rate", justify="right")
    table.add_column("Profit Factor", justify="right")

    for i, r in enumerate(results):
        m = r.metrics
        ret_color = "green" if m["total_return"] >= 0 else "red"
        table.add_row(
            f"#{i + 1}",
            r.strategy_name,
            f"[{ret_color}]{m['total_return']:+.2f}%[/{ret_color}]",
            f"{m['sharpe_ratio']:.3f}",
            f"[red]{m['max_drawdown']:.2f}%[/red]",
            str(m["total_trades"]),
            f"{m['win_rate']:.1f}%",
            f"{m['profit_factor']:.2f}",
        )

    console.print(table)


def cmd_strategies(args, config):
    """List available strategies."""
    console.print(BANNER)
    table = Table(title="Available Strategies", box=box.ROUNDED,
                  title_style="bold cyan")
    table.add_column("Name", style="cyan bold")
    table.add_column("Class", style="dim")
    table.add_column("Parameters", style="white")

    for name, cls in STRATEGY_MAP.items():
        instance = cls()
        params_str = ", ".join(f"{k}={v}" for k, v in instance.get_params().items())
        table.add_row(name, cls.__name__, params_str)

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Crypto Trading Bot — CCXT Powered",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", type=str, default=None,
                        help="Path to config YAML file")

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # backtest
    bt = sub.add_parser("backtest", help="Backtest a strategy")
    bt.add_argument("--strategy", "-s", default="sma_crossover",
                    choices=list_strategies())
    bt.add_argument("--pair", "-p", default="BTC/USDT")
    bt.add_argument("--timeframe", "-t", default="1h")
    bt.add_argument("--start", default=None, help="Start date (YYYY-MM-DD)")
    bt.add_argument("--limit", type=int, default=500)
    bt.add_argument("--no-charts", action="store_true")
    bt.add_argument("--show-trades", action="store_true")

    # paper-trade
    pt = sub.add_parser("paper-trade", help="Start paper trading")
    pt.add_argument("--strategy", "-s", default="sma_crossover",
                    choices=list_strategies())
    pt.add_argument("--pair", "-p", default="BTC/USDT")
    pt.add_argument("--timeframe", "-t", default="1h")

    # data
    dt = sub.add_parser("data", help="Fetch and display market data")
    dt.add_argument("--pair", "-p", default="BTC/USDT")
    dt.add_argument("--timeframe", "-t", default="1h")
    dt.add_argument("--limit", type=int, default=100)

    # compare
    cp = sub.add_parser("compare", help="Compare all strategies")
    cp.add_argument("--pair", "-p", default="BTC/USDT")
    cp.add_argument("--timeframe", "-t", default="1h")
    cp.add_argument("--start", default=None, help="Start date (YYYY-MM-DD)")
    cp.add_argument("--limit", type=int, default=500)

    # strategies
    sub.add_parser("strategies", help="List available strategies")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.command is None:
        parser.print_help()
        console.print("\n[yellow]Use one of the commands above to get started![/yellow]")
        return

    commands = {
        "backtest": cmd_backtest,
        "paper-trade": cmd_paper_trade,
        "data": cmd_data,
        "compare": cmd_compare,
        "strategies": cmd_strategies,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
