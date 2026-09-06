# Aegis Sentinel

**Continuous DeFi security agent** (public)

Live block monitoring · plain-language findings · Telegram/API · credit-loop design

Related private work: `aegisweb3-protosec` (full audit platform — **not** cloned here).

---

## Run

```bash
git clone https://github.com/A-Nuel/aegis-sentinel.git
cd aegis-sentinel
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

uvicorn app.main:app --reload --port 8000   # UI + API
python -m app.runner                          # continuous scans
python -m app.bot.telegram                    # optional
```

- Dashboard: http://127.0.0.1:8000/  
- API docs: http://127.0.0.1:8000/docs  
- Findings: http://127.0.0.1:8000/api/findings  

---

## Dual-repo map

| Repo | Role |
|------|------|
| **aegis-sentinel** (public) | Always-on monitor, public findings feed, alerts, self-funding agent loop |
| **aegisweb3-protosec** (private) | Deep audit / verification tooling — stays confidential |

Shared ideas only (patterns), never secrets, passwords, audit DBs, or internal reports.

---

## Features

- Multi-chain latest-block scan (flash-loan, whale, admin/pause, oracle heuristics)
- SQLite watches + alerts
- `/api/findings` with defensive “what this means / harden” text
- Simple dark UI dashboard
- Credit self-management stubs (OpenRouter / Orbio MCP ready)
- Telegram bot commands

---

## Roadmap (both repos)

**Public (sentinel)**  
1. Dashboard polish + severity filters  
2. Stronger detectors + watchlist UX  
3. Telegram push reliability  
4. Optional OpenRouter key for LLM summaries  

**Private (protosec)**  
1. Keep audit engine internal  
2. Optional bridge: “send address from sentinel → deep audit job” via local API only  
3. Never publish master password, JWT, allowlists, or audit DBs  
