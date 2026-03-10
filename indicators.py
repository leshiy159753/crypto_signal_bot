"""Technical indicator calculations: RSI, EMA, and RSI pivot detection."""

import pandas as pd
import numpy as np


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.inf)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def detect_rsi_peak(rsi_series: pd.Series, lookback: int = 3) -> bool:
    """
    Returns True if the candle at index [-lookback-1] is a confirmed RSI peak:
    higher than `lookback` candles on each side.
    """
    if len(rsi_series) < lookback * 2 + 2:
        return False
    idx = -(lookback + 1)
    pivot_val = rsi_series.iloc[idx]
    left  = rsi_series.iloc[idx - lookback : idx]
    right = rsi_series.iloc[idx + 1 : idx + 1 + lookback]
    if len(left) < lookback or len(right) < lookback:
        return False
    return bool((pivot_val > left).all() and (pivot_val > right).all())


def detect_rsi_bottom(rsi_series: pd.Series, lookback: int = 3) -> bool:
    """
    Returns True if the candle at index [-lookback-1] is a confirmed RSI bottom:
    lower than `lookback` candles on each side.
    """
    if len(rsi_series) < lookback * 2 + 2:
        return False
    idx = -(lookback + 1)
    pivot_val = rsi_series.iloc[idx]
    left  = rsi_series.iloc[idx - lookback : idx]
    right = rsi_series.iloc[idx + 1 : idx + 1 + lookback]
    if len(left) < lookback or len(right) < lookback:
        return False
    return bool((pivot_val < left).all() and (pivot_val < right).all())


def add_indicators(df: pd.DataFrame, rsi_period=14, ema_fast=21, ema_mid=50, ema_slow=200) -> pd.DataFrame:
    """Add RSI and EMA columns to OHLCV DataFrame."""
    df = df.copy()
    df["rsi"]      = calculate_rsi(df["close"], period=rsi_period)
    df["ema_fast"] = calculate_ema(df["close"], period=ema_fast)
    df["ema_mid"]  = calculate_ema(df["close"], period=ema_mid)
    df["ema_slow"] = calculate_ema(df["close"], period=ema_slow)
    return df
