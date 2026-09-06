# Aegis Sentinel

**Self-sustaining DeFi security agent for Orbio Build Week**

Continuous on-chain monitoring · Telegram + API alerts · Orbio MCP credit loop

This repo is **new and public**. It does **not** modify `aegisweb3-protosec`.

### What was ported vs left out

**Included (needed to run):**
- Live block threat scanning (flash-loan sigs, whale transfers, admin/pause calls)
- Multi-chain RPC with public failover (no private keys baked in)
- LLM severity scoring via OpenRouter (Orbio-claimed key)
- Continuous scan loop
- Telegram bot commands + alerts
- FastAPI dashboard API
- Local SQLite for watched contracts + alerts
- Credit-loop stub for Orbio MCP

**Left out (confidential / not needed for this challenge):**
- Master password, JWT secrets, IP allowlists
- Full multi-pass audit / HITL / forge verification stack
- Existing SQLite audit DBs and fork caches
- Internal enterprise report / mitigation pipeline

---

## Quick start

```bash
git clone https://github.com/A-Nuel/aegis-sentinel.git
cd aegis-sentinel
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — at least one RPC; optional TELEGRAM_* and OPENROUTER_API_KEY

# API
uvicorn app.main:app --reload --port 8000

# Continuous monitor (separate terminal)
python -m app.runner

# Telegram bot (optional)
python -m app.bot.telegram
```

API docs: http://127.0.0.1:8000/docs

---

## Orbio Build Week angle

1. Hold 1,000+ $ORBIO · apply at orbio.so/build
2. Claim $100 credits · put key in `OPENROUTER_API_KEY`
3. Wire Orbio MCP so the agent tops itself up
4. Keep project public by day 7

## Roadmap (7 days)

| Day | Focus |
|-----|--------|
| 0–1 | Apply, claim credits, run this base |
| 2 | Harden detectors + continuous loop |
| 3 | Telegram commands polish |
| 4 | Orbio MCP self-funding loop |
| 5 | Next.js dashboard |
| 6 | Demo video + README polish |
| 7 | Public final + submit |
