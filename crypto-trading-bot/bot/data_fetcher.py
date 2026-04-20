"""
Data Fetcher — CCXT Market Data Retrieval
==========================================
Fetches OHLCV, ticker, and order book data from crypto exchanges via CCXT.
Includes caching to minimize redundant API calls during backtesting.
"""

import time
import hashlib
import pickle
from pathlib import Path
from datetime import datetime, timezone

import ccxt
import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)

# ── In-memory + disk cache ──────────────────────────────────────────────

_CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
_MEMORY_CACHE: dict = {}


def _cache_key(exchange_id: str, symbol: str, timeframe: str, since: int, limit: int) -> str:
    """Generate a deterministic cache key."""
    raw = f"{exchange_id}:{symbol}:{timeframe}:{since}:{limit}"
    return hashlib.md5(raw.encode()).hexdigest()


def _save_to_disk(key: str, df: pd.DataFrame) -> None:
    """Persist DataFrame to disk as pickle."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _CACHE_DIR / f"{key}.pkl"
    df.to_pickle(path)


def _load_from_disk(key: str) -> pd.DataFrame | None:
    """Load a cached DataFrame from disk."""
    path = _CACHE_DIR / f"{key}.pkl"
    if path.exists():
        return pd.read_pickle(path)
    return None


# ── Exchange factory ────────────────────────────────────────────────────

def create_exchange(exchange_id: str = "binance", api_key: str = None,
                    api_secret: str = None) -> ccxt.Exchange:
    """
    Create and return a CCXT exchange instance.

    Args:
        exchange_id: CCXT exchange ID (e.g. 'binance', 'coinbase', 'kraken').
        api_key: Optional API key for authenticated endpoints.
        api_secret: Optional API secret.

    Returns:
        Configured ccxt.Exchange instance.
    """
    exchange_class = getattr(ccxt, exchange_id, None)
    if exchange_class is None:
        raise ValueError(f"Exchange '{exchange_id}' not found in CCXT. "
                         f"Available: {', '.join(ccxt.exchanges[:10])}...")

    config: dict = {"enableRateLimit": True}
    if api_key and api_secret:
        config["apiKey"] = api_key
        config["secret"] = api_secret

    exchange = exchange_class(config)
    logger.info(f"Initialized exchange: {exchange_id}")
    return exchange


# ── Data fetching ───────────────────────────────────────────────────────

def fetch_ohlcv(exchange: ccxt.Exchange, symbol: str = "BTC/USDT",
                timeframe: str = "1h", since: str = None,
                limit: int = 500, use_cache: bool = True) -> pd.DataFrame:
    """
    Fetch OHLCV (candlestick) data from an exchange.

    Args:
        exchange: CCXT exchange instance.
        symbol: Trading pair (e.g. 'BTC/USDT').
        timeframe: Candle timeframe ('1m','5m','15m','1h','4h','1d').
        since: Start date string (ISO format, e.g. '2025-01-01').
        limit: Max number of candles to fetch (per request).
        use_cache: Whether to use cached data.

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume, datetime.
    """
    since_ts = None
    if since:
        since_ts = exchange.parse8601(since + "T00:00:00Z")

    # Check cache
    cache_k = _cache_key(exchange.id, symbol, timeframe, since_ts or 0, limit)
    if use_cache:
        if cache_k in _MEMORY_CACHE:
            logger.debug("Returning OHLCV from memory cache")
            return _MEMORY_CACHE[cache_k].copy()
        disk_data = _load_from_disk(cache_k)
        if disk_data is not None:
            logger.debug("Returning OHLCV from disk cache")
            _MEMORY_CACHE[cache_k] = disk_data
            return disk_data.copy()

    logger.info(f"Fetching OHLCV: {symbol} {timeframe} "
                f"(since={since or 'latest'}, limit={limit})")

    all_candles = []
    fetch_since = since_ts

    # Paginated fetching for large date ranges
    while True:
        try:
            candles = exchange.fetch_ohlcv(
                symbol, timeframe, since=fetch_since, limit=limit
            )
        except ccxt.RateLimitExceeded:
            logger.warning("Rate limit hit, sleeping 10s...")
            time.sleep(10)
            continue
        except ccxt.NetworkError as e:
            logger.error(f"Network error: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error: {e}")
            raise

        if not candles:
            break

        all_candles.extend(candles)

        # If we got fewer than the limit, we've reached the end
        if len(candles) < limit:
            break

        # If no `since` was specified, we just wanted the latest batch
        if since_ts is None:
            break

        # Move the window forward (next candle after last received)
        fetch_since = candles[-1][0] + 1
        time.sleep(exchange.rateLimit / 1000)  # respect rate limits

    if not all_candles:
        logger.warning(f"No OHLCV data returned for {symbol}")
        return pd.DataFrame(columns=["timestamp", "open", "high", "low",
                                      "close", "volume", "datetime"])

    df = pd.DataFrame(all_candles,
                      columns=["timestamp", "open", "high", "low",
                                "close", "volume"])
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    # Cache it
    _MEMORY_CACHE[cache_k] = df.copy()
    _save_to_disk(cache_k, df)

    logger.info(f"Fetched {len(df)} candles for {symbol}")
    return df


def fetch_ticker(exchange: ccxt.Exchange, symbol: str = "BTC/USDT") -> dict:
    """
    Fetch the current ticker for a symbol.

    Returns:
        Dictionary with keys: symbol, last, bid, ask, high, low,
        volume, timestamp, datetime.
    """
    logger.info(f"Fetching ticker: {symbol}")
    try:
        ticker = exchange.fetch_ticker(symbol)
    except ccxt.BaseError as e:
        logger.error(f"Ticker fetch error: {e}")
        raise

    return {
        "symbol": ticker.get("symbol"),
        "last": ticker.get("last"),
        "bid": ticker.get("bid"),
        "ask": ticker.get("ask"),
        "high": ticker.get("high"),
        "low": ticker.get("low"),
        "volume": ticker.get("baseVolume"),
        "timestamp": ticker.get("timestamp"),
        "datetime": ticker.get("datetime"),
    }


def fetch_order_book(exchange: ccxt.Exchange, symbol: str = "BTC/USDT",
                     depth: int = 20) -> dict:
    """
    Fetch the order book for a symbol.

    Returns:
        Dictionary with 'bids' and 'asks' (each a list of [price, amount]).
    """
    logger.info(f"Fetching order book: {symbol} (depth={depth})")
    try:
        book = exchange.fetch_order_book(symbol, limit=depth)
    except ccxt.BaseError as e:
        logger.error(f"Order book fetch error: {e}")
        raise

    return {
        "bids": book.get("bids", [])[:depth],
        "asks": book.get("asks", [])[:depth],
        "timestamp": book.get("timestamp"),
    }


def get_available_pairs(exchange: ccxt.Exchange) -> list[str]:
    """Return a list of all trading pair symbols on the exchange."""
    exchange.load_markets()
    return sorted(exchange.symbols)


def clear_cache() -> None:
    """Clear both memory and disk caches."""
    global _MEMORY_CACHE
    _MEMORY_CACHE.clear()
    if _CACHE_DIR.exists():
        for f in _CACHE_DIR.glob("*.pkl"):
            f.unlink()
    logger.info("Cache cleared")
