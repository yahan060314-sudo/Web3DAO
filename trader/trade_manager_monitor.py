# Requirements: aiohttp, aiosqlite, fastapi, uvicorn, numpy
# Install: pip install aiohttp aiosqlite fastapi uvicorn numpy

import asyncio
import aiohttp
import aiosqlite
import json
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import math
import numpy as np
from typing import List, Dict, Any, Optional

# --------------------
# CONFIG
# --------------------
AGENTS = [
    {"name": "agent1", "url": "http://localhost:8001/metrics"},
    {"name": "agent2", "url": "http://localhost:8002/metrics"},
    {"name": "agent3", "url": "http://localhost:8003/metrics"},
]
POLL_INTERVAL = 10  # seconds
DB_PATH = "trade_manager_monitor.db"
SAMPLES_KEEP = 1000  # max samples to query for timeseries metrics

# Try to load an evaluation matrix definition from repo path api/evaluation_matrix.json if present.
# This file (if provided in your repo) should list additional metric keys to surface, e.g.:
# { "keys": ["confidence", "sharpe", "latency"] }
EVAL_MATRIX_PATH = os.path.join("api", "evaluation_matrix.json")
if os.path.exists(EVAL_MATRIX_PATH):
    try:
        with open(EVAL_MATRIX_PATH, "r", encoding="utf-8") as f:
            eval_matrix_def = json.load(f)
            EVAL_KEYS = eval_matrix_def.get("keys", [])
    except Exception:
        EVAL_KEYS = []
else:
    # sensible defaults based on common fields in this repo
    EVAL_KEYS = ["confidence", "trades", "wins", "losses", "cumulative_pl", "pl"]

# --------------------
# DB schema
# --------------------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    ts INTEGER NOT NULL,
    raw_json TEXT,
    balance REAL,
    pl REAL,
    cumulative_pl REAL,
    trades INTEGER,
    wins INTEGER,
    losses INTEGER,
    confidence REAL
);
CREATE INDEX IF NOT EXISTS idx_agent_ts ON samples(agent, ts);
"""

# --------------------
# APP
# --------------------
app = FastAPI(title="Trade Manager Monitor", version="1.0")

# --------------------
# DB helpers
# --------------------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLE_SQL)
        await db.commit()

async def save_sample(agent_name: str, data: dict):
    ts = int(data.get("timestamp", datetime.utcnow().timestamp()))
    balance = _safe_float(data.get("balance"))
    pl = _safe_float(data.get("pl"))
    cumulative_pl = _safe_float(data.get("cumulative_pl"))
    trades = _safe_int(data.get("trades"))
    wins = _safe_int(data.get("wins"))
    losses = _safe_int(data.get("losses"))
    confidence = _safe_float(data.get("confidence"))
    raw = json.dumps(data, default=str)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO samples (agent, ts, raw_json, balance, pl, cumulative_pl, trades, wins, losses, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (agent_name, ts, raw, balance, pl, cumulative_pl, trades, wins, losses, confidence),
        )
        await db.commit()

def _safe_float(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def _safe_int(v):
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None

# --------------------
# Polling
# --------------------
async def fetch_agent(session: aiohttp.ClientSession, agent: Dict[str, str]) -> Dict[str, Any]:
    try:
        async with session.get(agent["url"], timeout=5) as resp:
            if resp.status != 200:
                return {"error": f"status {resp.status}"}
            data = await resp.json()
            return data
    except Exception as e:
        return {"error": str(e)}

async def poll_loop():
    async with aiohttp.ClientSession() as session:
        while True:
            tasks = [fetch_agent(session, a) for a in AGENTS]
            results = await asyncio.gather(*tasks, return_exceptions=False)
            for agent, res in zip(AGENTS, results):
                if not isinstance(res, dict) or res.get("error"):
                    print(f"[{datetime.utcnow().isoformat()}] Error fetching {agent['name']}: {res.get('error') if isinstance(res, dict) else res}")
                    continue
                if "timestamp" not in res:
                    res["timestamp"] = int(datetime.utcnow().timestamp())
                await save_sample(agent["name"], res)
                print(f"[{datetime.utcnow().isoformat()}] Saved sample for {agent['name']}")
            await asyncio.sleep(POLL_INTERVAL)

# --------------------
# Metrics computation
# --------------------
async def fetch_samples(agent_name: str, limit: int = SAMPLES_KEEP) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT ts, raw_json, balance, pl, cumulative_pl, trades, wins, losses, confidence FROM samples WHERE agent=? ORDER BY ts DESC LIMIT ?",
            (agent_name, limit),
        )
        rows = await cur.fetchall()
    samples = []
    for r in rows:
        raw = {}
        try:
            raw = json.loads(r[1]) if r[1] else {}
        except Exception:
            raw = {}
        samples.append({
            "ts": r[0],
            "raw": raw,
            "balance": r[2],
            "pl": r[3],
            "cumulative_pl": r[4],
            "trades": r[5],
            "wins": r[6],
            "losses": r[7],
            "confidence": r[8],
        })
    # newest-first; caller may reverse if needed
    return samples

def compute_max_drawdown(series: List[float]) -> Optional[float]:
    if not series:
        return None
    peak = series[0]
    max_dd = 0.0
    for v in series:
        if v > peak:
            peak = v
        dd = (peak - v)
        if dd > max_dd:
            max_dd = dd
    return max_dd

def safe_div(a, b):
    try:
        if b in (0, None):
            return None
        return a / b
    except Exception:
        return None

async def compute_metrics_for_agent(agent_name: str) -> Dict[str, Any]:
    samples = await fetch_samples(agent_name, limit=SAMPLES_KEEP)
    if not samples:
        return {"agent": agent_name, "error": "no_samples"}

    # samples are newest-first; reverse for chronological
    samples = list(reversed(samples))

    latest = samples[-1]
    first = samples[0]

    # Baseline balance: use first known balance value in timeseries
    baseline_balance = None
    for s in samples:
        if s["balance"] is not None:
            baseline_balance = s["balance"]
            break

    latest_balance = latest.get("balance")
    p_percent = None
    if baseline_balance is not None and latest_balance is not None and baseline_balance != 0:
        p_percent = (latest_balance - baseline_balance) / baseline_balance * 100.0

    # Win share: prefer using wins/trades fields if present in the latest sample
    latest_trades = latest.get("trades")
    latest_wins = latest.get("wins")
    win_share = None
    if latest_trades is not None and latest_wins is not None and latest_trades > 0:
        win_share = latest_wins / latest_trades * 100.0

    # If wins/trades not present, try to infer from cumulative_pl changes (best-effort: count positive pl samples)
    if win_share is None:
        pos = sum(1 for s in samples if (s.get("pl") or 0) > 0)
        total = sum(1 for s in samples if s.get("pl") is not None)
        if total > 0:
            win_share = pos / total * 100.0

    # Confidence statistics
    confidences = [s["confidence"] for s in samples if s["confidence"] is not None]
    avg_confidence = float(np.mean(confidences)) if confidences else None
    median_confidence = float(np.median(confidences)) if confidences else None

    # Cumulative P&L series (prefer cumulative_pl else running sum of pl)
    cum_series = []
    if any(s.get("cumulative_pl") is not None for s in samples):
        for s in samples:
            v = s.get("cumulative_pl")
            if v is None:
                # fill forward/backward
                continue
            cum_series.append(float(v))
    else:
        # build running cumulative from pl's
        running = 0.0
        for s in samples:
            pl = s.get("pl")
            if pl is None:
                continue
            running += float(pl)
            cum_series.append(running)

    max_drawdown = compute_max_drawdown(cum_series) if cum_series else None
    avg_pl = None
    pls = [s["pl"] for s in samples if s.get("pl") is not None]
    if pls:
        avg_pl = float(np.mean(pls))

    # Sharpe-like ratio (mean / std of pl) annualization omitted (simple)
    sharpe = None
    if pls and len(pls) > 1:
        std = float(np.std(pls, ddof=1))
        if std != 0:
            sharpe = float(np.mean(pls) / std)

    # Evaluation matrix entries: attempt to collect latest values for keys listed in EVAL_KEYS
    eval_entries = {}
    latest_raw = latest.get("raw", {})
    for k in EVAL_KEYS:
        # look for key in latest raw JSON first, else in latest aggregate fields
        if k in latest_raw:
            eval_entries[k] = latest_raw.get(k)
        elif k in latest:
            eval_entries[k] = latest.get(k)
        else:
            # try to compute some derived keys
            if k == "win_rate":
                if latest_trades and latest_wins is not None:
                    eval_entries[k] = (latest_wins / latest_trades) * 100.0 if latest_trades > 0 else None
            elif k == "loss_rate":
                if latest_trades and latest_wins is not None:
                    eval_entries[k] = ((latest_trades - latest_wins) / latest_trades) * 100.0 if latest_trades > 0 else None
            else:
                eval_entries[k] = None

    metrics = {
        "agent": agent_name,
        "timestamp": int(datetime.utcnow().timestamp()),
        "latest": {
            "balance": latest_balance,
            "pl": latest.get("pl"),
            "cumulative_pl": latest.get("cumulative_pl"),
            "trades": latest_trades,
            "wins": latest_wins,
            "losses": latest.get("losses"),
            "confidence": latest.get("confidence"),
        },
        "computed": {
            "P_percent": None if p_percent is None else float(round(p_percent, 6)),
            "win_share_percent": None if win_share is None else float(round(win_share, 6)),
            "avg_confidence": None if avg_confidence is None else float(round(avg_confidence, 6)),
            "median_confidence": None if median_confidence is None else float(round(median_confidence, 6)),
            "avg_pl": None if avg_pl is None else float(round(avg_pl, 6)),
            "sharpe_like": None if sharpe is None else float(round(sharpe, 6)),
            "max_drawdown": None if max_drawdown is None else float(round(max_drawdown, 6)),
        },
        "evaluation_matrix": eval_entries,
        "timeseries": {
            "timestamps": [s["ts"] for s in samples],
            "balances": [s["balance"] for s in samples],
            "pl": [s["pl"] for s in samples],
            "cumulative_pl": cum_series,
            "confidence": [s["confidence"] for s in samples],
        },
    }

   *

