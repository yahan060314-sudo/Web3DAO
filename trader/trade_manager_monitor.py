# Requirements: aiohttp, aiosqlite, fastapi, uvicorn, numpy
# Install: pip install aiohttp aiosqlite fastapi uvicorn numpy

import asyncio
import aiohttp
import aiosqlite
import json
import os
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks
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

# Daily learning workflow configuration
DAILY_LOG_DIR = "logs"
LEARN_NOTIFY_PATH = "/learn"
LEARN_NOTIFY_TIMEOUT = 10
DAILY_RUN_HOUR_UTC = 0
DAILY_RUN_MIN_UTC = 0

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
    return metrics

# --------------------
# Daily Learning Workflow Helper Functions
# --------------------
def _ensure_log_dir():
    """Create DAILY_LOG_DIR if it doesn't exist."""
    Path(DAILY_LOG_DIR).mkdir(parents=True, exist_ok=True)

def _agent_base(a_url: str) -> str:
    """Return base URL by trimming last path segment."""
    return a_url.rsplit("/", 1)[0]

def _format_date(ts_or_datetime) -> str:
    """Format timestamp or datetime as YYYY-MM-DD."""
    if isinstance(ts_or_datetime, datetime):
        return ts_or_datetime.strftime("%Y-%m-%d")
    elif isinstance(ts_or_datetime, (int, float)):
        return datetime.utcfromtimestamp(ts_or_datetime).strftime("%Y-%m-%d")
    else:
        return str(ts_or_datetime)

async def _save_json(path: str, obj: dict):
    """Write JSON to file using asyncio.to_thread to avoid blocking event loop."""
    def _write():
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(obj, f, indent=2, default=str)
    await asyncio.to_thread(_write)

async def db_has_any_samples() -> bool:
    """Check if database has any samples."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM samples")
        row = await cur.fetchone()
        return row[0] > 0 if row else False

async def aggregate_daily_logs_for_date(target_date: datetime) -> Dict[str, Any]:
    """
    Aggregate daily logs for a specific UTC date.
    
    Computes start and end timestamps for the UTC date (00:00:00 to next day 00:00:00).
    For each agent in AGENTS, fetch samples via existing fetch_samples() with SAMPLES_KEEP
    then filter for samples in that time range.
    
    Compute basic per-agent stats: count_samples, trades, wins, pl_sum, avg_confidence,
    max_drawdown, timeseries arrays, and include the raw period_samples under raw_samples.
    
    Aggregate combined totals: total_trades, total_wins, total_pl.
    
    Save combined JSON to logs/combined_YYYY-MM-DD.json and each agent JSON to
    logs/{agent}_{YYYY-MM-DD}.json using _save_json.
    
    Returns an object containing the combined dict and paths.
    """
    _ensure_log_dir()
    
    # Compute start and end timestamps for the UTC date
    start_dt = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = start_dt + timedelta(days=1)
    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())
    
    date_str = _format_date(target_date)
    
    per_agent_data = {}
    combined_totals = {
        "total_trades": 0,
        "total_wins": 0,
        "total_pl": 0.0,
    }
    
    for agent in AGENTS:
        agent_name = agent["name"]
        
        # Fetch recent samples and filter for the date range
        all_samples = await fetch_samples(agent_name, limit=SAMPLES_KEEP)
        period_samples = [s for s in all_samples if start_ts <= s["ts"] < end_ts]
        
        # Compute basic stats
        count_samples = len(period_samples)
        
        # Trades: count samples with pl not None (proxy for trades)
        trades_count = sum(1 for s in period_samples if s.get("pl") is not None)
        
        # Wins: count samples with pl > 0
        wins_count = sum(1 for s in period_samples if (s.get("pl") or 0) > 0)
        
        # P&L sum
        pl_sum = sum(s.get("pl") or 0 for s in period_samples if s.get("pl") is not None)
        
        # Average confidence
        confidences = [s.get("confidence") for s in period_samples if s.get("confidence") is not None]
        avg_confidence = float(np.mean(confidences)) if confidences else None
        
        # Max drawdown: build cumulative P&L series
        cum_series = []
        running = 0.0
        for s in period_samples:
            pl = s.get("pl")
            if pl is not None:
                running += float(pl)
                cum_series.append(running)
        
        max_dd = compute_max_drawdown(cum_series) if cum_series else None
        
        # Timeseries arrays
        timeseries = {
            "timestamps": [s["ts"] for s in period_samples],
            "balances": [s.get("balance") for s in period_samples],
            "pl": [s.get("pl") for s in period_samples],
            "confidence": [s.get("confidence") for s in period_samples],
        }
        
        agent_summary = {
            "agent": agent_name,
            "date": date_str,
            "count_samples": count_samples,
            "trades": trades_count,
            "wins": wins_count,
            "pl_sum": round(pl_sum, 6) if pl_sum else 0.0,
            "avg_confidence": round(avg_confidence, 6) if avg_confidence is not None else None,
            "max_drawdown": round(max_dd, 6) if max_dd is not None else None,
            "timeseries": timeseries,
            "raw_samples": [
                {
                    "ts": s["ts"],
                    "balance": s.get("balance"),
                    "pl": s.get("pl"),
                    "cumulative_pl": s.get("cumulative_pl"),
                    "trades": s.get("trades"),
                    "wins": s.get("wins"),
                    "losses": s.get("losses"),
                    "confidence": s.get("confidence"),
                }
                for s in period_samples
            ],
        }
        
        per_agent_data[agent_name] = agent_summary
        
        # Update combined totals
        combined_totals["total_trades"] += trades_count
        combined_totals["total_wins"] += wins_count
        combined_totals["total_pl"] += pl_sum
        
        # Save per-agent log
        agent_log_path = os.path.join(DAILY_LOG_DIR, f"{agent_name}_{date_str}.json")
        await _save_json(agent_log_path, agent_summary)
    
    # Build combined summary
    combined_summary = {
        "date": date_str,
        "combined_totals": {
            "total_trades": combined_totals["total_trades"],
            "total_wins": combined_totals["total_wins"],
            "total_pl": round(combined_totals["total_pl"], 6),
            "win_rate": round(combined_totals["total_wins"] / combined_totals["total_trades"] * 100, 2)
                if combined_totals["total_trades"] > 0 else None,
        },
        "per_agent": per_agent_data,
    }
    
    # Save combined log
    combined_log_path = os.path.join(DAILY_LOG_DIR, f"combined_{date_str}.json")
    await _save_json(combined_log_path, combined_summary)
    
    return {
        "combined_summary": combined_summary,
        "combined_path": combined_log_path,
        "per_agent_paths": {
            agent_name: os.path.join(DAILY_LOG_DIR, f"{agent_name}_{date_str}.json")
            for agent_name in per_agent_data.keys()
        },
    }

def generate_learning_prompt_for_agent(agent_name: str, agent_summary: dict, combined_summary: dict) -> str:
    """
    Build a human-readable prompt string instructing the agent to learn from the day's data
    and return a JSON object with insights and actions.
    
    The prompt includes summary stats and instructs the agent to consider other agents'
    successful patterns.
    """
    prompt = f"""
# Daily Learning Report for {agent_name} - {agent_summary.get('date')}

## Your Performance Today
- Samples collected: {agent_summary.get('count_samples', 0)}
- Trades executed: {agent_summary.get('trades', 0)}
- Wins: {agent_summary.get('wins', 0)}
- Total P&L: {agent_summary.get('pl_sum', 0)}
- Average Confidence: {agent_summary.get('avg_confidence', 'N/A')}
- Max Drawdown: {agent_summary.get('max_drawdown', 'N/A')}

## Combined System Performance
- Total Trades: {combined_summary.get('combined_totals', {}).get('total_trades', 0)}
- Total Wins: {combined_summary.get('combined_totals', {}).get('total_wins', 0)}
- Total P&L: {combined_summary.get('combined_totals', {}).get('total_pl', 0)}
- Win Rate: {combined_summary.get('combined_totals', {}).get('win_rate', 'N/A')}%

## Other Agents' Performance
"""
    
    per_agent = combined_summary.get('per_agent', {})
    for other_name, other_summary in per_agent.items():
        if other_name != agent_name:
            prompt += f"""
- {other_name}:
  - Trades: {other_summary.get('trades', 0)}
  - Wins: {other_summary.get('wins', 0)}
  - P&L: {other_summary.get('pl_sum', 0)}
  - Avg Confidence: {other_summary.get('avg_confidence', 'N/A')}
"""
    
    prompt += """
## Instructions
Please analyze the performance data provided and return a JSON object with the following structure:
{
  "insights": [
    "List of key insights from today's performance",
    "Patterns observed in successful trades",
    "Areas that need improvement"
  ],
  "actions": [
    "Specific actions to take based on today's learning",
    "Parameter adjustments to consider",
    "Strategies to adopt from other agents if applicable"
  ],
  "learned_from_others": [
    "Patterns or strategies from other agents that could be beneficial"
  ]
}

Consider the following in your analysis:
1. Your win rate compared to the system average
2. Confidence levels on winning vs. losing trades
3. Drawdown patterns and risk management
4. Successful patterns from other agents that might apply to your strategy
5. Market conditions that affected performance

Return only the JSON object, no additional text.
"""
    
    return prompt

async def notify_agents_learning(combined_obj: dict, target_date: datetime, timeout: int) -> dict:
    """
    POST to each agent's base_url + LEARN_NOTIFY_PATH with payload containing:
    date, agent name, agent summary, combined summary, prompt string, and the full
    per-agent daily log.
    
    Capture responses and errors in a results dict.
    """
    results = {}
    combined_summary = combined_obj["combined_summary"]
    per_agent_data = combined_summary.get("per_agent", {})
    date_str = _format_date(target_date)
    
    async with aiohttp.ClientSession() as session:
        for agent in AGENTS:
            agent_name = agent["name"]
            agent_url = agent["url"]
            
            try:
                base_url = _agent_base(agent_url)
                learn_url = f"{base_url}{LEARN_NOTIFY_PATH}"
                
                agent_summary = per_agent_data.get(agent_name, {})
                prompt = generate_learning_prompt_for_agent(agent_name, agent_summary, combined_summary)
                
                payload = {
                    "date": date_str,
                    "agent": agent_name,
                    "summary": agent_summary,
                    "combined": combined_summary,
                    "prompt": prompt,
                    "raw_samples": agent_summary.get("raw_samples", []),
                }
                
                async with session.post(learn_url, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    response_text = await resp.text()
                    results[agent_name] = {
                        "status": resp.status,
                        "response": response_text,
                    }
                    print(f"[{datetime.utcnow().isoformat()}] Notified {agent_name} learning endpoint: status={resp.status}")
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                results[agent_name] = {"error": error_msg}
                print(f"[{datetime.utcnow().isoformat()}] Error notifying {agent_name}: {error_msg}")
    
    return results

async def run_daily_learning_for_date(target_date: datetime) -> dict:
    """
    Run daily learning workflow for a specific date.
    
    Calls aggregate_daily_logs_for_date and then notify_agents_learning and
    returns combined path and notify results.
    """
    try:
        print(f"[{datetime.utcnow().isoformat()}] Starting daily learning for date: {_format_date(target_date)}")
        
        # Aggregate logs
        aggregation_result = await aggregate_daily_logs_for_date(target_date)
        print(f"[{datetime.utcnow().isoformat()}] Aggregation complete. Combined log: {aggregation_result['combined_path']}")
        
        # Notify agents
        notify_results = await notify_agents_learning(aggregation_result, target_date, LEARN_NOTIFY_TIMEOUT)
        print(f"[{datetime.utcnow().isoformat()}] Agent notifications complete")
        
        return {
            "date": _format_date(target_date),
            "combined_path": aggregation_result["combined_path"],
            "per_agent_paths": aggregation_result["per_agent_paths"],
            "notify_results": notify_results,
        }
    except Exception as e:
        error_msg = f"Error in run_daily_learning_for_date: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"[{datetime.utcnow().isoformat()}] {error_msg}")
        return {
            "error": error_msg,
            "date": _format_date(target_date),
        }

# --------------------
# Daily Scheduler
# --------------------
def _seconds_until_next_run(hour: int, minute: int) -> float:
    """Compute seconds until next run at given UTC hour/minute."""
    now = datetime.utcnow()
    # Target time today
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If target time has passed today, schedule for tomorrow
    if target <= now:
        target += timedelta(days=1)
    
    delta = target - now
    return delta.total_seconds()

async def daily_scheduler_loop():
    """
    Sleep until next run, call run_daily_learning_for_date for current UTC date,
    and repeat daily. Log start/finish/errors.
    """
    print(f"[{datetime.utcnow().isoformat()}] Daily scheduler started. Will run at {DAILY_RUN_HOUR_UTC:02d}:{DAILY_RUN_MIN_UTC:02d} UTC")
    
    while True:
        try:
            # Calculate wait time
            wait_seconds = _seconds_until_next_run(DAILY_RUN_HOUR_UTC, DAILY_RUN_MIN_UTC)
            print(f"[{datetime.utcnow().isoformat()}] Next daily learning run in {wait_seconds:.0f} seconds")
            
            # Sleep until next run
            await asyncio.sleep(wait_seconds)
            
            # Run for previous UTC day (the day that just ended)
            target_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            
            print(f"[{datetime.utcnow().isoformat()}] Starting scheduled daily learning run")
            result = await run_daily_learning_for_date(target_date)
            print(f"[{datetime.utcnow().isoformat()}] Scheduled daily learning run complete: {result.get('combined_path', 'N/A')}")
            
        except Exception as e:
            error_msg = f"Error in daily_scheduler_loop: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            print(f"[{datetime.utcnow().isoformat()}] {error_msg}")
            # Sleep for a bit before retrying to avoid tight loop on persistent errors
            await asyncio.sleep(60)

# --------------------
# FastAPI Endpoints
# --------------------
@app.post("/admin/run_learning_now")
async def run_learning_now(background_tasks: BackgroundTasks):
    """
    Admin endpoint to trigger the aggregation on demand.
    
    Schedules run_daily_learning_for_date for the current UTC date as a background task
    and returns JSONResponse indicating scheduled and the date.
    """
    target_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    date_str = _format_date(target_date)
    
    # Schedule as background task
    background_tasks.add_task(run_daily_learning_for_date, target_date)
    
    return JSONResponse({
        "status": "scheduled",
        "message": f"Daily learning workflow scheduled for date: {date_str}",
        "date": date_str,
    })

# --------------------
# Startup Handler
# --------------------
@app.on_event("startup")
async def startup_event():
    """Initialize database and start background tasks."""
    print(f"[{datetime.utcnow().isoformat()}] Starting Trade Manager Monitor")
    
    # Initialize database
    await init_db()
    print(f"[{datetime.utcnow().isoformat()}] Database initialized")
    
    # Start polling loop
    asyncio.create_task(poll_loop())
    print(f"[{datetime.utcnow().isoformat()}] Polling loop started")
    
    # Start daily scheduler
    asyncio.create_task(daily_scheduler_loop())
    print(f"[{datetime.utcnow().isoformat()}] Daily scheduler started")

