"""Telegram alerts. Run separately once TELEGRAM_BOT_TOKEN is set."""

from __future__ import annotations

import asyncio

from app.config import settings
from app.engine.sentinel import sentinel


async def notify(text: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    from telegram import Bot

    bot = Bot(settings.telegram_bot_token)
    await bot.send_message(chat_id=settings.telegram_chat_id, text=text)


async def poll_and_alert() -> None:
    seen: set[str] = set()
    while True:
        result = sentinel.scan_latest_block("ethereum")
        for alert in result.get("alerts") or []:
            aid = alert.get("id")
            if aid in seen:
                continue
            seen.add(aid)
            await notify(
                f"[{alert.get('severity')}] {alert.get('type')} on {alert.get('chain')}\n"
                f"{alert.get('details')}\n"
                f"tx: {alert.get('tx_hash')}"
            )
        await asyncio.sleep(settings.scan_interval_seconds)


if __name__ == "__main__":
    asyncio.run(poll_and_alert())
