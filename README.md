# Aegis Sentinel

Self-sustaining DeFi security agent for **Orbio Build Week**.

Continuous on-chain monitoring, Telegram + web alerts, and an Orbio MCP loop so the agent can claim, watch, and top up its own inference credits.

This is a **new repo**. It does not modify `aegisweb3-protosec`. Patterns are adapted from that project's Threat Sentinel (live block scan, flash-loan / whale / admin detectors) and rebuilt as a public agent.

## What it does

- Watch contract addresses on Ethereum / Arbitrum / Base
- Detect flash-loan signatures, large transfers, pause / ownership changes
- Ask an LLM (via Orbio / OpenRouter key) to score severity
- Alert on Telegram and show a live web dashboard
- Self-manage Orbio credits (balance → claim key → spend → top up / rotate)

## Stack

- Python 3.11+ / FastAPI / web3.py
- Telegram bot
- Next.js dashboard (coming next)
- Orbio MCP + OpenRouter key

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill RPC, TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY (claimed from Orbio)
uvicorn app.main:app --reload --port 8000
```

Dashboard API: http://127.0.0.1:8000/docs

## Status

Day 0 scaffold. Next: wire live RPC scan loop + Telegram + MCP credit manager.
