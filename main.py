"""
Main entry point for the Crypto Signal Bot.
APScheduler loop monitors all symbols and timeframes.
"""

import asyncio
import logging
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from fetcher import fetch_ohlcv
from indicators import add_indicators
from signals import check_signals, format_signal
from bot import send_signal, close_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def scan(symbol: str, timeframe: str) -> None:
    try:
        logger.info(f"Scanning {symbol} / {timeframe}")
        df = fetch_ohlcv(symbol, timeframe, limit=500)
        df = add_indicators(
            df,
            rsi_period=config.RSI_PERIOD,
            ema_fast=config.EMA_FAST,
            ema_mid=config.EMA_MID,
            ema_slow=config.EMA_SLOW,
        )
        signals = check_signals(df, symbol, timeframe)
        if signals:
            for sig in signals:
                text = format_signal(sig)
                logger.info(f"Signal: {sig.signal_type} for {symbol} {timeframe}")
                await send_signal(text)
        else:
            logger.debug(f"No signal for {symbol} {timeframe}")
    except Exception as e:
        logger.error(f"Error scanning {symbol}/{timeframe}: {e}")


async def main() -> None:
    scheduler = AsyncIOScheduler()

    for timeframe in config.TIMEFRAMES:
        interval_seconds = config.POLL_INTERVAL.get(timeframe, 300)
        for symbol in config.SYMBOLS:
            scheduler.add_job(
                scan,
                "interval",
                seconds=interval_seconds,
                args=[symbol, timeframe],
                id=f"{symbol}_{timeframe}",
                next_run_time=datetime.datetime.now(),
            )

    scheduler.start()
    logger.info("Bot started. Monitoring: %s on %s", config.SYMBOLS, config.TIMEFRAMES)

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        scheduler.shutdown()
        await close_bot()


if __name__ == "__main__":
    asyncio.run(main())
