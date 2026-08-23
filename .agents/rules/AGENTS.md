---
trigger: always_on
---

# SATP AI Workspace Rules & Protocols

> **AUTOMATIC LOAD INSTRUCTION:** This file defines compulsory guidelines for all AI coding agents working on the Smart Algorithmic Trading Platform (SATP).

---

## 1. MANDATORY PRE-CODING PROTOCOL

Before proposing or making ANY source code changes:

1. **Inspect `SYSTEM_BLUEPRINT.md` First:** Always read [SYSTEM_BLUEPRINT.md](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/SYSTEM_BLUEPRINT.md) before performing deep code research. It contains the single-source-of-truth index for architecture, strategy registry, and parameter schemas.
2. **Formulate a Plan:** Outline the technical design, affected files, and verification plan.
3. **Obtain User Alignment:** Present the proposed plan clearly and await explicit confirmation unless executing minor debug actions requested directly by the user.

---

## 2. TOKEN PRESERVATION & EFFICIENCY DIRECTIVES

To maintain fast response times and prevent context window exhaustion:

1. **Targeted File Inspection:**
   - NEVER read entire files over 300 lines using `view_file` without line limits.
   - ALWAYS specify `StartLine` and `EndLine` to read only the specific target function or class block.
2. **Compact Logging:**
   - Never stream long terminal outputs (e.g. running 180-day backtests with verbose per-bar printing) directly into conversation history.
   - Redirect verbose command outputs to log files or scratch summary scripts.
3. **Scratch Analysis Scripts:**
   - Place temporary research, data inspection, and sanity-check scripts inside the `<appDataDir>\brain\<conversation-id>/scratch/` or workspace `scratch/` directory.

---

## 3. CORE REPOSITORY CONTRACTS & GUARDRAILS

AI agents MUST obey these non-negotiable repository rules:

1. **Virtual Environment Execution:**
   - The user's system runs inside a Python virtual environment (`venv`).
   - ALWAYS run shell/Python commands using `..\venv\Scripts\python.exe` on Windows.
   - NEVER suggest or execute Docker commands or reliance on Docker containers.
2. **Strategy Range Loop Rule:**
   - All strategy registration loops, configuration registries, and backtest runner loops MUST use `range(1, 21)` (strategies 1 through 20).
3. **Database Driver Convention:**
   - `DATABASE_URL` uses `asyncpg` (async driver) for FastAPI.
   - `DB_SYNC_URL` uses `psycopg2` (sync driver) for Alembic migrations.
   - Hostname inside containers is `'db'`, host on local development machine is `'localhost'`.
4. **Dhan API Token Validation:**
   - Dhan API tokens expire every 24 hours. Always check token validity before diagnosing API errors.
5. **Dynamic Override Integrity:**
   - Never remove or bypass `strategy_overrides` or dynamic parameter reloading in `instruments.json` and `accounts.json`.
6. **Documentation Synchronization:**
   - Any addition of new strategies or configuration parameters must be documented in `STRATEGY_DEVELOPMENT_GUIDE.md`, `CONFIGURATION_GUIDE.md`, and `SYSTEM_BLUEPRINT.md`.
7. **Git Destructive Action Prevention:**
   - NEVER run destructive git commands like \git restore\, \git reset\, or \git clean\ without EXPLICIT permission from the user.
   - If you make a mistake editing a file, use IDE editing tools (\multi_replace_file_content\) or restore from IDE backups/transcript logs, rather than relying on git which may destroy the user's uncommitted work.
