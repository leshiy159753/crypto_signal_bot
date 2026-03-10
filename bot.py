"""Telegram bot: send signal messages using aiogram."""

import asyncio
import logging
from aiogram import Bot
from aiogram.enums import ParseMode
import config

logger = logging.getLogger(__name__)

_bot: Bot = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=config.TELEGRAM_TOKEN)
    return _bot


async def send_message(text: str) -> None:
    """Send a message to the configured Telegram chat."""
    bot = get_bot()
    try:
        await bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")


async def send_signal(text: str) -> None:
    """Alias for send_message for clarity."""
    await send_message(text)


async def close_bot() -> None:
    """Close the bot session gracefully."""
    bot = get_bot()
    await bot.session.close()
