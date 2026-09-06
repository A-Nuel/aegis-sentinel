"""Telegram bot: commands + explained alert pushes."""

from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.engine.credits import credit_loop
from app.engine.explain import explain_alert
from app.engine.sentinel import sentinel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("telegram")


async def notify(text: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    from telegram import Bot

    bot = Bot(settings.telegram_bot_token)
    await bot.send_message(chat_id=settings.telegram_chat_id, text=text[:4000])


def format_finding(alert: dict) -> str:
    exp = explain_alert(alert)
    return (
        f"[{exp.get('severity')}] {exp.get('title') or exp.get('type')}\n"
        f"chain: {exp.get('chain')}\n"
        f"{exp.get('means') or exp.get('raw_details')}\n"
        f"Harden: {exp.get('harden')}\n"
        f"tx: {exp.get('tx_hash') or 'n/a'}"
    )


async def poll_alerts() -> None:
    seen: set[str] = set()
    for a in sentinel.recent_alerts(100):
        if a.get("id"):
            seen.add(str(a["id"]))
    while True:
        enrich = bool(settings.llm_api_key)
        for chain in settings.chains_list:
            result = sentinel.scan_latest_block(chain, enrich=enrich)
            for alert in result.get("alerts") or []:
                aid = str(alert.get("id"))
                if aid in seen:
                    continue
                seen.add(aid)
                await notify(format_finding(alert))
        await asyncio.sleep(settings.scan_interval_seconds)


async def run_bot() -> None:
    if not settings.telegram_bot_token:
        log.warning("TELEGRAM_BOT_TOKEN missing")
        if settings.telegram_chat_id:
            await poll_alerts()
        return

    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes

    app = Application.builder().token(settings.telegram_bot_token).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Aegis Sentinel online.\n"
            "/status /credits /watch <addr> [chain] /unwatch <addr> [chain]\n"
            "/scan [chain] /scanall /alerts /findings"
        )

    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            f"watched={len(sentinel.watched)} "
            f"alerts={len(sentinel.recent_alerts(20))} "
            f"orbio_key={'yes' if settings.llm_api_key else 'no'}"
        )

    async def credits_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        s = credit_loop.ensure_funded()
        await update.message.reply_text(
            f"action={s.get('action')} remaining={s.get('remaining_usd')}\n"
            f"base={settings.llm_base_url}"
        )

    async def watch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            await update.message.reply_text("Usage: /watch 0x... [chain]")
            return
        addr = context.args[0]
        chain = context.args[1] if len(context.args) > 1 else "ethereum"
        item = sentinel.watch(addr, chain)
        await update.message.reply_text(f"Watching {item}")

    async def unwatch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            await update.message.reply_text("Usage: /unwatch 0x... [chain]")
            return
        addr = context.args[0]
        chain = context.args[1] if len(context.args) > 1 else "ethereum"
        ok = sentinel.unwatch(addr, chain)
        await update.message.reply_text(f"removed={ok}")

    async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chain = context.args[0] if context.args else "ethereum"
        result = sentinel.scan_latest_block(chain, enrich=bool(settings.llm_api_key))
        await update.message.reply_text(
            f"Scanned {chain}: {result['new_alerts']} new"
        )

    async def scanall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        n = 0
        for chain in settings.chains_list:
            r = sentinel.scan_latest_block(chain, enrich=bool(settings.llm_api_key))
            n += r.get("new_alerts", 0)
        await update.message.reply_text(f"Scanned all chains: {n} new alerts")

    async def alerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        rows = sentinel.recent_alerts(5)
        if not rows:
            await update.message.reply_text("No alerts yet")
            return
        await update.message.reply_text(
            "\n\n".join(format_finding(a) for a in rows)[:4000]
        )

    async def findings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await alerts_cmd(update, context)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("credits", credits_cmd))
    app.add_handler(CommandHandler("watch", watch_cmd))
    app.add_handler(CommandHandler("unwatch", unwatch_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.add_handler(CommandHandler("scanall", scanall_cmd))
    app.add_handler(CommandHandler("alerts", alerts_cmd))
    app.add_handler(CommandHandler("findings", findings_cmd))

    asyncio.create_task(poll_alerts())
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    log.info("Telegram bot running")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(run_bot())
