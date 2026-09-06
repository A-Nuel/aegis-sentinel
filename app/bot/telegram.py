"""Telegram bot: /start /status /watch /scan /alerts"""

from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.engine.sentinel import sentinel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("telegram")


async def notify(text: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    from telegram import Bot

    bot = Bot(settings.telegram_bot_token)
    await bot.send_message(chat_id=settings.telegram_chat_id, text=text[:4000])


async def poll_alerts() -> None:
    seen: set[str] = set()
    while True:
        for chain in settings.chains_list:
            result = sentinel.scan_latest_block(chain, enrich=False)
            for alert in result.get("alerts") or []:
                aid = str(alert.get("id"))
                if aid in seen:
                    continue
                seen.add(aid)
                await notify(
                    f"🚨 [{alert.get('severity')}] {alert.get('type')}\n"
                    f"chain: {alert.get('chain')}\n"
                    f"{alert.get('details')}\n"
                    f"tx: {alert.get('tx_hash')}"
                )
        await asyncio.sleep(settings.scan_interval_seconds)


async def run_bot() -> None:
    if not settings.telegram_bot_token:
        log.warning("TELEGRAM_BOT_TOKEN missing — alert poller only if CHAT_ID set")
        await poll_alerts()
        return

    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes

    app = Application.builder().token(settings.telegram_bot_token).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Aegis Sentinel online.\nCommands: /status /watch <addr> [chain] /scan [chain] /alerts"
        )

    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            f"watched={len(sentinel.watched)} recent_alerts={len(sentinel.recent_alerts(10))}"
        )

    async def watch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            await update.message.reply_text("Usage: /watch 0x... [chain]")
            return
        addr = context.args[0]
        chain = context.args[1] if len(context.args) > 1 else "ethereum"
        item = sentinel.watch(addr, chain)
        await update.message.reply_text(f"Watching {item}")

    async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chain = context.args[0] if context.args else "ethereum"
        result = sentinel.scan_latest_block(chain, enrich=False)
        await update.message.reply_text(
            f"Scanned {chain}: {result['new_alerts']} new alerts"
        )

    async def alerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        rows = sentinel.recent_alerts(5)
        if not rows:
            await update.message.reply_text("No alerts yet")
            return
        lines = [f"{a.get('severity')} {a.get('type')} @ {a.get('chain')}" for a in rows]
        await update.message.reply_text("\n".join(lines))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("watch", watch_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.add_handler(CommandHandler("alerts", alerts_cmd))

    asyncio.create_task(poll_alerts())
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    log.info("Telegram bot running")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(run_bot())
