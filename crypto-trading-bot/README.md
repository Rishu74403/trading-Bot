<p align="center">
  <h1 align="center">⟠ Crypto Trading Bot</h1>
  <p align="center">
    <strong>A Python-powered cryptocurrency trading bot with CCXT, multiple strategies, and a full backtesting engine.</strong>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.9+-blue?style=flat-square&logo=python" alt="Python">
    <img src="https://img.shields.io/badge/CCXT-4.0+-orange?style=flat-square" alt="CCXT">
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
    <img src="https://img.shields.io/badge/status-active-brightgreen?style=flat-square" alt="Status">
  </p>
</p>

---

## ✨ Features

- 📊 **Market Data via CCXT** — Fetch OHLCV, ticker, and order book data from 100+ exchanges
- 📈 **4 Built-in Strategies** — SMA Crossover, RSI Mean Reversion, MACD Signal, Bollinger Bands
- 🧪 **Backtesting Engine** — Full historical simulation with fees, slippage, and stop-loss/take-profit
- 📉 **Performance Metrics** — Sharpe ratio, max drawdown, win rate, profit factor, and more
- 📝 **Paper Trading** — Simulate live trading without risking real capital
- 🖥️ **Web Dashboard** — Dark-themed Flask dashboard with interactive Chart.js charts
- 🎨 **Rich CLI** — Beautiful terminal output with colored tables and ASCII art
- 🔧 **Configurable** — YAML config with environment variable override support
- 🧩 **Extensible** — Easy to add custom strategies via the base `Strategy` class
- ✅ **Tested** — Unit tests for indicators, strategies, and backtesting logic

---

## 📁 Project Structure

```
crypto-trading-bot/
├── main.py                 # CLI entry point
├── dashboard.py            # Flask web dashboard
├── requirements.txt        # Python dependencies
├── setup.py                # Package setup
├── config/
│   ├── __init__.py         # Config loader (YAML + env vars)
│   └── settings.yaml       # Bot configuration
├── bot/
│   ├── __init__.py
│   ├── data_fetcher.py     # CCXT data fetching with caching
│   ├── indicators.py       # Technical indicators (SMA, RSI, MACD, etc.)
│   ├── strategies.py       # Trading strategies
│   ├── backtester.py       # Backtesting engine
│   ├── portfolio.py        # Portfolio & position management
│   └── trader.py           # Paper trading engine
├── utils/
│   ├── __init__.py
│   ├── logger.py           # Rich logging
│   └── plotting.py         # Matplotlib chart generation
└── tests/
    ├── test_indicators.py
    ├── test_strategies.py
    └── test_backtester.py
```

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/crypto-trading-bot.git
cd crypto-trading-bot
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run a backtest
```bash
python main.py backtest --strategy sma_crossover --pair BTC/USDT --timeframe 1h
```

---

## 💻 CLI Usage

```bash
# Backtest a strategy
python main.py backtest -s sma_crossover -p BTC/USDT -t 1h --limit 500 --show-trades

# Compare all strategies
python main.py compare -p BTC/USDT -t 1h --limit 500

# Fetch live market data
python main.py data -p ETH/USDT -t 4h --limit 50

# Start paper trading
python main.py paper-trade -s rsi -p BTC/USDT -t 1h

# List available strategies
python main.py strategies
```

### Available Strategies

| Strategy | Key | Description |
|----------|-----|-------------|
| SMA Crossover | `sma_crossover` | Buy/sell on fast/slow SMA crossover |
| RSI Mean Reversion | `rsi` | Buy oversold (RSI < 30), sell overbought (RSI > 70) |
| MACD Signal | `macd` | Buy/sell on MACD/signal line crossover |
| Bollinger Bands | `bollinger_bands` | Buy at lower band, sell at upper band |

---

## 🖥️ Web Dashboard

Launch the interactive web dashboard:

```bash
python dashboard.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

Features:
- Run backtests with custom parameters
- Interactive equity curve and price charts
- Strategy comparison table
- Trade log viewer

---

## ⚙️ Configuration

Edit `config/settings.yaml` to customize:

```yaml
exchange: binance
trading_pair: BTC/USDT
timeframe: 1h
initial_capital: 10000.0
fee_rate: 0.001
strategy: sma_crossover
stop_loss: 0.05
take_profit: 0.10
```

You can also override with environment variables:
```bash
export CRYPTO_PAIR=ETH/USDT
export CRYPTO_STRATEGY=macd
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 🧩 Adding Custom Strategies

Create a new strategy by extending the `Strategy` base class:

```python
from bot.strategies import Strategy, STRATEGY_MAP
from bot.indicators import add_rsi, add_sma

class MyStrategy(Strategy):
    def __init__(self, **kwargs):
        super().__init__(kwargs)

    def get_name(self) -> str:
        return "My Custom Strategy"

    def generate_signals(self, df):
        df = df.copy()
        # ... add your logic here ...
        df["signal"] = 0  # 1=buy, -1=sell, 0=hold
        return df

# Register it
STRATEGY_MAP["my_strategy"] = MyStrategy
```

---

## ⚠️ Disclaimer

This bot is for **educational and research purposes only**. Cryptocurrency trading involves significant risk. Do not use this bot with real money without thorough testing and understanding of the risks involved. Past performance does not guarantee future results.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
