"""
Signal logic: detect trading signals based on RSI peak/bottom pivots and EMA proximity.

Signal types:
  RSI_PEAK_SHORT   — RSI formed a confirmed peak in 80-90 zone while price was rising -> probable short
  RSI_BOTTOM_LONG  — RSI formed a confirmed bottom in 3-30 zone while price was falling -> probable long
  EMA_APPROACH     — Price approaching lower EMA band (4h+ only) -> watch zone alert
  EMA_TOUCH_SHORT  — Price touching/near EMA with RSI in overbought zone (80-90) -> probable short
  EMA_TOUCH_LONG   — Price touching/near EMA with RSI in oversold zone (3-30) -> probable long
  BULL_CROSS       — EMA21 crosses above EMA50 (legacy)
  BEAR_CROSS       — EMA21 crosses below EMA50 (legacy)
"""

from dataclasses import dataclass, field
from typing import Optional, List
import pandas as pd
import config
from indicators import detect_rsi_peak, detect_rsi_bottom


@dataclass
class Signal:
    symbol: str
    timeframe: str
    signal_type: str
    rsi: float
    ema_fast: float
    ema_mid: float
    ema_slow: float
    close: float
    timestamp: str
    reasoning: str = ""


_last_signal: dict = {}


def _pct_diff(price: float, ema: float) -> float:
    """Percentage difference between price and EMA."""
    return abs(price - ema) / ema * 100


def check_signals(df: pd.DataFrame, symbol: str, timeframe: str) -> List[Signal]:
    """
    Analyze the latest candles and return a list of Signals if conditions are met.
    Returns empty list if no signals or all are duplicates.
    """
    if len(df) < config.EMA_SLOW + 10:
        return []

    last = df.iloc[-1]
    prev = df.iloc[-2]

    rsi      = last["rsi"]
    ema_fast = last["ema_fast"]
    ema_mid  = last["ema_mid"]
    ema_slow = last["ema_slow"]
    close    = last["close"]
    ts       = str(last["open_time"])

    rsi_series  = df["rsi"]
    pivot_lb    = config.PIVOT_LOOKBACK

    # Pivot RSI value (the candle being confirmed as peak/bottom)
    pivot_rsi = rsi_series.iloc[-(pivot_lb + 1)] if len(rsi_series) >= pivot_lb + 2 else rsi

    signals: List[Signal] = []

    # --- 1. RSI PEAK -> SHORT ---
    if pivot_rsi >= config.RSI_OB_LOW and detect_rsi_peak(rsi_series, pivot_lb):
        sig_type = "RSI_PEAK_SHORT"
        key = f"{symbol}_{timeframe}_{sig_type}"
        if _last_signal.get(key) != round(pivot_rsi, 1):
            reasoning = (
                f"RSI достиг зоны перекупленности ({pivot_rsi:.1f}, диапазон {config.RSI_OB_LOW}-{config.RSI_OB_HIGH}) "
                f"и сформировал подтверждённый пик. Цена росла, но импульс угасает. "
                f"Высокая вероятность разворота вниз — вероятный ШОРТ."
            )
            signals.append(Signal(
                symbol=symbol, timeframe=timeframe, signal_type=sig_type,
                rsi=round(pivot_rsi, 2), ema_fast=round(ema_fast, 2),
                ema_mid=round(ema_mid, 2), ema_slow=round(ema_slow, 2),
                close=round(close, 2), timestamp=ts, reasoning=reasoning,
            ))
            _last_signal[key] = round(pivot_rsi, 1)

    # --- 2. RSI BOTTOM -> LONG ---
    if pivot_rsi <= config.RSI_OS_HIGH and detect_rsi_bottom(rsi_series, pivot_lb):
        sig_type = "RSI_BOTTOM_LONG"
        key = f"{symbol}_{timeframe}_{sig_type}"
        if _last_signal.get(key) != round(pivot_rsi, 1):
            reasoning = (
                f"RSI достиг зоны перепроданности ({pivot_rsi:.1f}, диапазон {config.RSI_OS_LOW}-{config.RSI_OS_HIGH}) "
                f"и сформировал подтверждённое дно. Цена снижалась, но продавцы теряют силу. "
                f"Высокая вероятность отскока вверх — вероятный ЛОНГ."
            )
            signals.append(Signal(
                symbol=symbol, timeframe=timeframe, signal_type=sig_type,
                rsi=round(pivot_rsi, 2), ema_fast=round(ema_fast, 2),
                ema_mid=round(ema_mid, 2), ema_slow=round(ema_slow, 2),
                close=round(close, 2), timestamp=ts, reasoning=reasoning,
            ))
            _last_signal[key] = round(pivot_rsi, 1)

    # --- EMA proximity signals (4h, 1d, 1w, 1M only) ---
    if timeframe in config.EMA_SIGNAL_TIMEFRAMES:
        emas = {"EMA21": ema_fast, "EMA50": ema_mid, "EMA200": ema_slow}
        below_emas = {name: val for name, val in emas.items() if val < close}

        if below_emas:
            nearest_name = min(below_emas, key=lambda k: close - below_emas[k])
            nearest_val  = below_emas[nearest_name]
            pct = _pct_diff(close, nearest_val)

            # --- 3. EMA APPROACH ---
            if pct <= config.EMA_APPROACH_PCT:
                sig_type = "EMA_APPROACH"
                key = f"{symbol}_{timeframe}_{sig_type}"
                if _last_signal.get(key) != nearest_name:
                    reasoning = (
                        f"Цена ({close:.2f}) приближается к скользящей {nearest_name} ({nearest_val:.2f}) "
                        f"на {pct:.2f}% (порог {config.EMA_APPROACH_PCT}%). "
                        f"Уровень может выступить поддержкой или быть пробит. Следите за реакцией цены."
                    )
                    signals.append(Signal(
                        symbol=symbol, timeframe=timeframe, signal_type=sig_type,
                        rsi=round(rsi, 2), ema_fast=round(ema_fast, 2),
                        ema_mid=round(ema_mid, 2), ema_slow=round(ema_slow, 2),
                        close=round(close, 2), timestamp=ts, reasoning=reasoning,
                    ))
                    _last_signal[key] = nearest_name

            # --- 4. EMA TOUCH + RSI overbought -> SHORT ---
            if pct <= config.EMA_APPROACH_PCT and config.RSI_OB_LOW <= rsi <= config.RSI_OB_HIGH:
                sig_type = "EMA_TOUCH_SHORT"
                key = f"{symbol}_{timeframe}_{sig_type}"
                if _last_signal.get(key) != round(rsi, 1):
                    reasoning = (
                        f"Цена касается {nearest_name} ({nearest_val:.2f}) при RSI в зоне перекупленности ({rsi:.1f}). "
                        f"Совпадение касания скользящей и перегрева RSI ({config.RSI_OB_LOW}-{config.RSI_OB_HIGH}) "
                        f"— высокая вероятность отбоя вниз. Вероятный ШОРТ."
                    )
                    signals.append(Signal(
                        symbol=symbol, timeframe=timeframe, signal_type=sig_type,
                        rsi=round(rsi, 2), ema_fast=round(ema_fast, 2),
                        ema_mid=round(ema_mid, 2), ema_slow=round(ema_slow, 2),
                        close=round(close, 2), timestamp=ts, reasoning=reasoning,
                    ))
                    _last_signal[key] = round(rsi, 1)

            # --- 5. EMA TOUCH + RSI oversold -> LONG ---
            if pct <= config.EMA_APPROACH_PCT and config.RSI_OS_LOW <= rsi <= config.RSI_OS_HIGH:
                sig_type = "EMA_TOUCH_LONG"
                key = f"{symbol}_{timeframe}_{sig_type}"
                if _last_signal.get(key) != round(rsi, 1):
                    reasoning = (
                        f"Цена касается {nearest_name} ({nearest_val:.2f}) при RSI в зоне перепроданности ({rsi:.1f}). "
                        f"Совпадение касания скользящей и истощения продавцов (RSI {config.RSI_OS_LOW}-{config.RSI_OS_HIGH}) "
                        f"— высокая вероятность отскока вверх. Вероятный ЛОНГ."
                    )
                    signals.append(Signal(
                        symbol=symbol, timeframe=timeframe, signal_type=sig_type,
                        rsi=round(rsi, 2), ema_fast=round(ema_fast, 2),
                        ema_mid=round(ema_mid, 2), ema_slow=round(ema_slow, 2),
                        close=round(close, 2), timestamp=ts, reasoning=reasoning,
                    ))
                    _last_signal[key] = round(rsi, 1)

    # --- 6. Legacy EMA cross signals ---
    if prev["ema_fast"] < prev["ema_mid"] and ema_fast > ema_mid:
        sig_type = "BULL_CROSS"
        key = f"{symbol}_{timeframe}_{sig_type}"
        if _last_signal.get(key) != "active":
            signals.append(Signal(
                symbol=symbol, timeframe=timeframe, signal_type=sig_type,
                rsi=round(rsi, 2), ema_fast=round(ema_fast, 2),
                ema_mid=round(ema_mid, 2), ema_slow=round(ema_slow, 2),
                close=round(close, 2), timestamp=ts,
                reasoning="EMA21 пересекла EMA50 снизу вверх — бычий крест, возможное продолжение роста.",
            ))
            _last_signal[key] = "active"
    elif prev["ema_fast"] > prev["ema_mid"] and ema_fast < ema_mid:
        sig_type = "BEAR_CROSS"
        key = f"{symbol}_{timeframe}_{sig_type}"
        if _last_signal.get(key) != "active":
            signals.append(Signal(
                symbol=symbol, timeframe=timeframe, signal_type=sig_type,
                rsi=round(rsi, 2), ema_fast=round(ema_fast, 2),
                ema_mid=round(ema_mid, 2), ema_slow=round(ema_slow, 2),
                close=round(close, 2), timestamp=ts,
                reasoning="EMA21 пересекла EMA50 сверху вниз — медвежий крест, возможное продолжение падения.",
            ))
            _last_signal[key] = "active"

    return signals


def format_signal(sig: Signal) -> str:
    """Format a Signal object into a Telegram HTML message."""
    icons = {
        "RSI_PEAK_SHORT":  "🔴",
        "RSI_BOTTOM_LONG": "🟢",
        "EMA_APPROACH":    "⚠️",
        "EMA_TOUCH_SHORT": "🔴",
        "EMA_TOUCH_LONG":  "🟢",
        "BULL_CROSS":      "📈",
        "BEAR_CROSS":      "📉",
    }
    labels = {
        "RSI_PEAK_SHORT":  "ВЕРОЯТНЫЙ ШОРТ — RSI Перекупленность",
        "RSI_BOTTOM_LONG": "ВЕРОЯТНЫЙ ЛОНГ — RSI Перепроданность",
        "EMA_APPROACH":    "ПРИБЛИЖЕНИЕ К СКОЛЬЗЯЩИМ",
        "EMA_TOUCH_SHORT": "ВЕРОЯТНЫЙ ШОРТ — Касание EMA + Перекупленность",
        "EMA_TOUCH_LONG":  "ВЕРОЯТНЫЙ ЛОНГ — Касание EMA + Перепроданность",
        "BULL_CROSS":      "Бычий крест EMA (EMA21 x EMA50)",
        "BEAR_CROSS":      "Медвежий крест EMA (EMA21 x EMA50)",
    }
    icon  = icons.get(sig.signal_type, "⚡")
    label = labels.get(sig.signal_type, sig.signal_type)

    return (
        f"{icon} <b>СИГНАЛ [{sig.symbol} | {sig.timeframe}]</b>\n"
        f"📊 RSI: <b>{sig.rsi}</b>\n"
        f"📈 EMA21: {sig.ema_fast} | EMA50: {sig.ema_mid} | EMA200: {sig.ema_slow}\n"
        f"💲 Цена: <b>{sig.close}</b>\n"
        f"💡 Направление: <b>{label}</b>\n"
        f"📝 Обоснование: {sig.reasoning}\n"
        f"⏰ {sig.timestamp}"
    )
