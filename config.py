# Configuration for Crypto Signal Bot
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8654500635:AAGZnrc2unNKjg4KX3DKapc0_FXi3hEkIQU")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "391843334")

SYMBOLS = ["BTCUSDT", "ETHUSDT"]

# 15m/1h = RSI peak/bottom signals only
# 4h/1d/1w/1M = RSI peak/bottom + EMA proximity signals
TIMEFRAMES = ["15m", "1h", "4h", "1d", "1w", "1M"]

RSI_PERIOD = 14

# Overbought zone: RSI 80-90 -> watch for peak reversal -> SHORT signal
RSI_OB_LOW  = 80
RSI_OB_HIGH = 90

# Oversold zone: RSI 3-30 (corresponds to "-97 to -70") -> watch for bottom -> LONG signal
RSI_OS_HIGH = 30
RSI_OS_LOW  = 3

RSI_OVERSOLD   = 30
RSI_OVERBOUGHT = 70

EMA_FAST = 21
EMA_MID  = 50
EMA_SLOW = 200

# % distance from price to EMA to trigger "approaching" alert
EMA_APPROACH_PCT = 1.5

# Only these timeframes emit EMA proximity signals
EMA_SIGNAL_TIMEFRAMES = ["4h", "1d", "1w", "1M"]

# Number of candles each side to confirm RSI pivot peak/bottom
PIVOT_LOOKBACK = 3

POLL_INTERVAL = {
    "15m": 60 * 5,
    "1h":  60 * 15,
    "4h":  60 * 60,
    "1d":  60 * 60 * 4,
    "1w":  60 * 60 * 12,
    "1M":  60 * 60 * 24,
}

BINANCE_API_KEY    = ""
BINANCE_API_SECRET = ""
