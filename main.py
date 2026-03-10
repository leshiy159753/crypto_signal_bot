"""
Main entry point for the Crypto Signal Bot.
APScheduler loop monitors all symbols and timeframes.
Aiogram Dispatcher handles /start, /scan, /status commands.
"""

import asyncio
import logging
import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

import config
from fetcher import fetch_ohlcv
from indicators import add_indicators
from signals import check_signals, format_signal
from bot import send_signal, get_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

dp = Dispatcher()
_start_time = datetime.datetime.now(datetime.timezone.utc)


async def scan_pair(symbol: str, timeframe: str) -> list:
    df = fetch_ohlcv(symbol, timeframe, limit=500)
    df = add_indicators(
        df,
        rsi_period=config.RSI_PERIOD,
        ema_period=config.EMA_PERIOD,
    )
    signals = check_signals(df, symbol, timeframe)
    return signals


async def run_scan(notify: bool = True) -> list:
    """Scan all pairs/timeframes. If notify=True, send signals to Telegram."""
    all_signals = []
    for symbol in config.SYMBOLS:
        for tf in config.TIMEFRAMES:
            logger.info(f"Scanning {symbol} / {tf}")
            try:
                signals = await scan_pair(symbol, tf)
                all_signals.extend(signals)
                if notify:
                    for sig in signals:
                        msg = format_signal(sig)
                        await send_signal(msg)
            except Exception as e:
                logger.error(f"Error scanning {symbol}/{tf}: {e}")
    return all_signals


@dp.message(Command("start"))
async def cmd_start(message: Message):
    pairs = ", ".join(config.SYMBOLS)
    tfs = ", ".join(config.TIMEFRAMES)
    text = (
        f"Crypto Signal Bot running!\n"
        f"Pairs: {pairs}\n"
        f"Timeframes: {tfs}\n\n"
        f"Commands:\n"
        f"/scan — run scan now\n"
        f"/status — bot uptime"
    )
    await message.answer(text)


@dp.message(Command("scan"))
async def cmd_scan(message: Message):
    await message.answer("Scanning all pairs... please wait.")
    signals = await run_scan(notify=False)
    if not signals:
        await message.answer("No signals found. Market is neutral.")
    else:
        for sig in signals:
            await message.answer(format_signal(sig), parse_mode=ParseMode.HTML)


@dp.message(Command("status"))
async def cmd_status(message: Message):
    uptime = datetime.datetime.now(datetime.timezone.utc) - _start_time
    hours, rem = divmod(int(uptime.total_seconds()), 3600)
    minutes = rem // 60
    pairs = ", ".join(config.SYMBOLS)
    tfs = ", ".join(config.TIMEFRAMES)
    text = (
        f"Bot uptime: {hours}h {minutes}m\n"
        f"Monitoring: {pairs}\n"
        f"Timeframes: {tfs}"
    )
    await message.answer(text)


async def main():
    bot = get_bot()

    scheduler = AsyncIOScheduler()
    interval_map = {
        "15m": 15, "1h": 60, "4h": 240,
        "1d": 1440, "1w": 10080, "1M": 43200,
    }
    for symbol in config.SYMBOLS:
        for tf in config.TIMEFRAMES:
            minutes = interval_map.get(tf, 60)
            scheduler.add_job(
                run_scan,
                "interval",
                minutes=minutes,
                kwargs={"notify": True},
                id=f"scan_{symbol}_{tf}",
            )

    scheduler.start()
    logger.info(
        f"Bot started. Monitoring: {config.SYMBOLS} on {config.TIMEFRAMES}"
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
