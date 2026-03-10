"""Fetch OHLCV candlestick data from Binance public API."""

import requests
import pandas as pd


BINANCE_BASE = "https://data-api.binance.vision/api/v3/klines"


def fetch_ohlcv(symbol: str, interval: str, limit: int = 250) -> pd.DataFrame:
    """
    Fetch OHLCV data from Binance for given symbol and interval.
    Returns a DataFrame with columns: open_time, open, high, low, close, volume
    """
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    resp = requests.get(BINANCE_BASE, params=params, timeout=10)
    resp.raise_for_status()
    raw = resp.json()

    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    return df[["open_time", "open", "high", "low", "close", "volume"]]
