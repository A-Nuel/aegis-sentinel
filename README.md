# Aegis Sentinel

**Self-sustaining DeFi security agent — Orbio Build Week**

Continuous on-chain monitoring · Telegram + API · credit self-management loop

Repo: public and separate from private `aegisweb3-protosec`.

---

## Timeline reality (6 Sept 2026)

| Phase | Status |
|-------|--------|
| **Apply** | Closing **today (Sunday)** — hold 1,000+ $ORBIO and apply at [orbio.so/build](https://www.orbio.so/build) **now** |
| **Build** | **7 days after you are approved** — not ending today |
| **Judging** | 3 days after build |
| **Projects** | Must be **public by day 7** of build |

Approvals were still happening on 6 Sept. If you are not on the approved list yet, apply immediately.

---

## Quick start

```bash
git clone https://github.com/A-Nuel/aegis-sentinel.git
cd aegis-sentinel
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set OPENROUTER_API_KEY after Orbio credits land

uvicorn app.main:app --reload --port 8000   # API
python -m app.runner                          # continuous agent
python -m app.bot.telegram                    # optional alerts
```

- Health: http://127.0.0.1:8000/health  
- Docs: http://127.0.0.1:8000/docs  
- Credits: `GET /api/credits` · `POST /api/credits/ensure`

---

## Self-funding loop (Orbio differentiator)

1. Claim key from Orbio balance (dashboard or MCP).
2. Put it in `OPENROUTER_API_KEY`.
3. Runner calls `ensure_funded()` every cycle — checks OpenRouter key status, logs top-up need under threshold.
4. With Claude Code MCP:

```bash
claude mcp add --transport http --scope user orbio https://www.orbio.so/api/mcp
# then /mcp → Authenticate with holding wallet
```

Tools: `orbio_get_balance`, `orbio_claim_key`, `orbio_get_key_status`, `orbio_top_up_key`, `orbio_rotate_key`, `orbio_delete_key`.

---

## Detectors (MVP)

- Flash-loan calldata signatures  
- Large native transfers (≥ 500 units)  
- Admin / pause / ownership patterns  
- Oracle touch heuristics  
- Optional LLM severity scoring via Orbio/OpenRouter  

---

## Build order

1. **Today:** Apply + hold tokens  
2. Claim $100 credits → `.env`  
3. Run API + runner  
4. Telegram  
5. Full MCP top-up path  
6. Next.js dashboard  
7. Demo + public README for judges  
