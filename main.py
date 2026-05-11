"""
MayaTermux V14.0 — Self-Upgrading AI Crypto Intelligence + Global Internet + OS Nexus
"""
import os
import ast
import time
import sqlite3
import threading
import importlib.util
import json
import textwrap
import xml.etree.ElementTree as ET
import subprocess
import shlex
from typing import Optional

import requests
import ccxt
import pandas as pd
from google import genai
from google.genai import types

# ── Config ────────────────────────────────────────────────────────────────────
BOSS_ID        = os.environ.get("BOSS_ID", "SUPREME_BOSS_01")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
EXCHANGE_ID    = os.environ.get("EXCHANGE_ID", "binance")
PAPER_BALANCE  = float(os.environ.get("PAPER_BALANCE", "10000"))
LEARN_INTERVAL = int(os.environ.get("LEARN_INTERVAL_SEC", "600"))   # 10-minute cycle

if not GEMINI_API_KEY:
    raise EnvironmentError("Set GEMINI_API_KEY environment variable before running.")

_CLIENT  = genai.Client(api_key=GEMINI_API_KEY)
_MODEL   = "gemini-2.0-flash"           # fast + capable
_DB      = "maya_vault.db"
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "MayaTermux/14.0 (crypto-research-bot)"})


# ── DB Helper ─────────────────────────────────────────────────────────────────
def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS intel (
            id INTEGER PRIMARY KEY,
            topic TEXT, data TEXT, ts TEXT
        );
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            task TEXT,
            description TEXT,
            version INTEGER DEFAULT 1,
            path TEXT,
            usage_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            last_error TEXT,
            ts TEXT
        );
        CREATE TABLE IF NOT EXISTS skill_versions (
            id INTEGER PRIMARY KEY,
            name TEXT, version INTEGER, path TEXT, ts TEXT
        );
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY,
            topic TEXT, tags TEXT, insight TEXT, ts TEXT
        );
        CREATE TABLE IF NOT EXISTS paper_account (
            id INTEGER PRIMARY KEY, usdt_balance REAL, ts TEXT
        );
        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY,
            symbol TEXT, side TEXT, amount REAL,
            price REAL, pnl REAL, ts TEXT
        );
    """)
    conn.commit()
    conn.close()


# ── Web Intelligence ─────────────────────────────────────────────────────────
class WebIntelligence:
    """
    Pulls live macro & sentiment data from public internet APIs.
    All sources are free, no API key required.
    """

    # ── Fear & Greed ─────────────────────────────────────────────────────────
    def fear_greed(self) -> dict:
        """Alternative.me Crypto Fear & Greed Index."""
        try:
            r = _SESSION.get("https://api.alternative.me/fng/?limit=3", timeout=8)
            r.raise_for_status()
            data = r.json()["data"]
            latest = data[0]
            return {
                "value":       int(latest["value"]),
                "label":       latest["value_classification"],
                "yesterday":   int(data[1]["value"]) if len(data) > 1 else None,
                "last_week":   int(data[2]["value"]) if len(data) > 2 else None,
            }
        except Exception as e:
            return {"error": str(e)}

    # ── CoinGecko Global Market ───────────────────────────────────────────────
    def global_market(self) -> dict:
        """Global crypto market cap, dominance, volume."""
        try:
            r = _SESSION.get("https://api.coingecko.com/api/v3/global", timeout=10)
            r.raise_for_status()
            d = r.json()["data"]
            return {
                "total_market_cap_usd":  round(d["total_market_cap"]["usd"] / 1e9, 2),  # $B
                "total_volume_24h_usd":  round(d["total_volume"]["usd"] / 1e9, 2),
                "btc_dominance":         round(d["market_cap_percentage"]["btc"], 2),
                "eth_dominance":         round(d["market_cap_percentage"].get("eth", 0), 2),
                "market_cap_change_24h": round(d["market_cap_change_percentage_24h_usd"], 2),
                "active_coins":          d["active_cryptocurrencies"],
            }
        except Exception as e:
            return {"error": str(e)}

    # ── Trending Coins ────────────────────────────────────────────────────────
    def trending(self) -> list[dict]:
        """Top-7 trending coins on CoinGecko."""
        try:
            r = _SESSION.get("https://api.coingecko.com/api/v3/search/trending", timeout=10)
            r.raise_for_status()
            coins = r.json()["coins"]
            return [
                {
                    "rank":   c["item"]["market_cap_rank"],
                    "name":   c["item"]["name"],
                    "symbol": c["item"]["symbol"].upper(),
                    "score":  round(c["item"].get("score", 0), 2),
                }
                for c in coins[:7]
            ]
        except Exception as e:
            return [{"error": str(e)}]

    # ── Top Movers ────────────────────────────────────────────────────────────
    def top_movers(self, top_n: int = 5) -> dict:
        """Biggest gainers and losers (top-250 by market cap)."""
        try:
            r = _SESSION.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order":       "market_cap_desc",
                    "per_page":    250,
                    "page":        1,
                    "price_change_percentage": "24h",
                },
                timeout=12,
            )
            r.raise_for_status()
            coins = r.json()
            sorted_by_change = sorted(
                [c for c in coins if c.get("price_change_percentage_24h") is not None],
                key=lambda x: x["price_change_percentage_24h"],
            )
            losers  = sorted_by_change[:top_n]
            gainers = sorted_by_change[-top_n:][::-1]
            def fmt(c):
                return f"{c['symbol'].upper()} {c['price_change_percentage_24h']:+.2f}%"
            return {
                "gainers": [fmt(c) for c in gainers],
                "losers":  [fmt(c) for c in losers],
            }
        except Exception as e:
            return {"error": str(e)}

    # ── News Headlines via RSS ────────────────────────────────────────────────
    def news(self, limit: int = 6) -> list[str]:
        """Latest crypto headlines from CoinDesk RSS."""
        try:
            r = _SESSION.get("https://www.coindesk.com/arc/outboundfeeds/rss/", timeout=10)
            r.raise_for_status()
            root  = ET.fromstring(r.content)
            items = root.findall(".//item")[:limit]
            return [item.findtext("title", "").strip() for item in items]
        except Exception:
            # Fallback: CoinTelegraph
            try:
                r = _SESSION.get("https://cointelegraph.com/rss", timeout=10)
                r.raise_for_status()
                root  = ET.fromstring(r.content)
                items = root.findall(".//item")[:limit]
                return [item.findtext("title", "").strip() for item in items]
            except Exception as e:
                return [f"News unavailable: {e}"]

    # ── Bitcoin On-Chain (mempool.space) ─────────────────────────────────────
    def btc_mempool(self) -> dict:
        """BTC mempool size and recommended fees from mempool.space."""
        try:
            fees = _SESSION.get("https://mempool.space/api/v1/fees/recommended", timeout=8)
            fees.raise_for_status()
            f = fees.json()
            mempool = _SESSION.get("https://mempool.space/api/mempool", timeout=8)
            mempool.raise_for_status()
            m = mempool.json()
            return {
                "mempool_tx_count": m.get("count", "?"),
                "mempool_size_mb":  round(m.get("vsize", 0) / 1e6, 2),
                "fee_fastest_sat":  f.get("fastestFee"),
                "fee_hour_sat":     f.get("hourFee"),
                "fee_economy_sat":  f.get("economyFee"),
            }
        except Exception as e:
            return {"error": str(e)}

    # ── Composite Snapshot ────────────────────────────────────────────────────
    def snapshot(self) -> dict:
        """Fetch all web intel in parallel and return a unified dict."""
        results = {}
        lock    = threading.Lock()

        def fetch(key, fn):
            data = fn()
            with lock:
                results[key] = data

        tasks = [
            ("fear_greed",    self.fear_greed),
            ("global_market", self.global_market),
            ("trending",      self.trending),
            ("top_movers",    self.top_movers),
            ("news",          self.news),
            ("btc_mempool",   self.btc_mempool),
        ]
        threads = [threading.Thread(target=fetch, args=(k, fn)) for k, fn in tasks]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return results

    def format_snapshot(self, snap: dict) -> str:
        lines = ["\n── Global Web Intel ─────────────────────────────────────"]

        fg = snap.get("fear_greed", {})
        if "error" not in fg:
            lines.append(
                f"  Fear & Greed : {fg['value']} ({fg['label']}) "
                f"| Yesterday: {fg['yesterday']} | Last Week: {fg['last_week']}"
            )

        gm = snap.get("global_market", {})
        if "error" not in gm:
            lines.append(
                f"  Market Cap   : ${gm['total_market_cap_usd']}B "
                f"({gm['market_cap_change_24h']:+.2f}% 24h)"
            )
            lines.append(
                f"  Volume 24h   : ${gm['total_volume_24h_usd']}B "
                f"| BTC Dom: {gm['btc_dominance']}% | ETH Dom: {gm['eth_dominance']}%"
            )

        movers = snap.get("top_movers", {})
        if "error" not in movers:
            lines.append(f"  Top Gainers  : {', '.join(movers.get('gainers', []))}")
            lines.append(f"  Top Losers   : {', '.join(movers.get('losers', []))}")

        trend = snap.get("trending", [])
        if trend and "error" not in trend[0]:
            names = ", ".join(f"{t['symbol']}(#{t['rank']})" for t in trend[:5])
            lines.append(f"  Trending     : {names}")

        mempool = snap.get("btc_mempool", {})
        if "error" not in mempool:
            lines.append(
                f"  BTC Mempool  : {mempool['mempool_tx_count']} txs "
                f"| Fee fastest/hour: {mempool['fee_fastest_sat']}/{mempool['fee_hour_sat']} sat/vB"
            )

        news = snap.get("news", [])
        if news:
            lines.append("  Headlines    :")
            for h in news[:4]:
                lines.append(f"    • {h}")

        return "\n".join(lines)


# ── Technical Indicators ──────────────────────────────────────────────────────
class Indicators:
    @staticmethod
    def rsi(s: pd.Series, p: int = 14) -> pd.Series:
        d = s.diff()
        g = d.clip(lower=0).rolling(p).mean()
        loss = (-d.clip(upper=0)).rolling(p).mean()
        return 100 - (100 / (1 + g / loss.replace(0, float("nan"))))

    @staticmethod
    def macd(s: pd.Series, fast=12, slow=26, sig=9):
        m = s.ewm(span=fast, adjust=False).mean() - s.ewm(span=slow, adjust=False).mean()
        sl = m.ewm(span=sig, adjust=False).mean()
        return m, sl, m - sl

    @staticmethod
    def bollinger(s: pd.Series, p=20, k=2):
        sma = s.rolling(p).mean()
        std = s.rolling(p).std()
        return sma + k * std, sma, sma - k * std

    @staticmethod
    def ema(s: pd.Series, p: int) -> pd.Series:
        return s.ewm(span=p, adjust=False).mean()

    @staticmethod
    def atr(df: pd.DataFrame, p: int = 14) -> pd.Series:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"]  - df["close"].shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(p).mean()

    @staticmethod
    def stoch_rsi(s: pd.Series, p=14) -> pd.Series:
        rsi = Indicators.rsi(s, p)
        min_r = rsi.rolling(p).min()
        max_r = rsi.rolling(p).max()
        return (rsi - min_r) / (max_r - min_r).replace(0, float("nan"))

    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        tp = (df["high"] + df["low"] + df["close"]) / 3
        return (tp * df["vol"]).cumsum() / df["vol"].cumsum()


# ── Market Engine ─────────────────────────────────────────────────────────────
class MarketEngine:
    def __init__(self, exchange_id: str = "binance"):
        self.exchange: ccxt.Exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})

    def ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> pd.DataFrame:
        raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df  = pd.DataFrame(raw, columns=["time", "open", "high", "low", "close", "vol"])
        df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
        return df

    def ticker(self, symbol: str) -> dict:
        return self.exchange.fetch_ticker(symbol)

    def full_analysis(self, symbol: str, timeframe: str = "1h") -> dict:
        df    = self.ohlcv(symbol, timeframe, limit=100)
        close = df["close"]

        rsi_v           = Indicators.rsi(close).iloc[-1]
        _, _, hist      = Indicators.macd(close)
        bb_u, bb_m, bb_l = Indicators.bollinger(close)
        atr_v           = Indicators.atr(df).iloc[-1]
        ema9            = Indicators.ema(close, 9).iloc[-1]
        ema21           = Indicators.ema(close, 21).iloc[-1]
        ema50           = Indicators.ema(close, 50).iloc[-1]
        srsi            = Indicators.stoch_rsi(close).iloc[-1]
        vwap_v          = Indicators.vwap(df).iloc[-1]
        price           = close.iloc[-1]
        vol_avg         = df["vol"].rolling(20).mean().iloc[-1]
        vol_ratio       = df["vol"].iloc[-1] / vol_avg if vol_avg else 1.0

        signals = [
            1  if rsi_v < 30  else (-1 if rsi_v > 70  else 0),
            1  if hist.iloc[-1] > 0 else -1,
            1  if ema9 > ema21 else -1,
            1  if ema21 > ema50 else -1,
            1  if price > bb_m.iloc[-1] else -1,
            1  if price > vwap_v else -1,
            1  if srsi < 0.2   else (-1 if srsi > 0.8 else 0),
        ]
        score = sum(signals) / len(signals)

        return {
            "symbol":    symbol,
            "timeframe": timeframe,
            "price":     round(price, 4),
            "rsi":       round(rsi_v, 2),
            "stoch_rsi": round(float(srsi), 3) if srsi == srsi else None,
            "macd_hist": round(hist.iloc[-1], 4),
            "ema9":      round(ema9, 4),
            "ema21":     round(ema21, 4),
            "ema50":     round(ema50, 4),
            "vwap":      round(vwap_v, 4),
            "bb_upper":  round(bb_u.iloc[-1], 4),
            "bb_lower":  round(bb_l.iloc[-1], 4),
            "atr":       round(atr_v, 4),
            "vol_ratio": round(vol_ratio, 2),
            "score":     round(score, 2),
            "signal":    ("STRONG BUY"  if score >= 0.7 else
                          "BUY"         if score >= 0.3 else
                          "STRONG SELL" if score <= -0.7 else
                          "SELL"        if score <= -0.3 else "NEUTRAL"),
        }


# ── Knowledge Base ────────────────────────────────────────────────────────────
class KnowledgeBase:
    """Persistent memory of market insights, trade lessons and AI conclusions."""

    def store(self, topic: str, insight: str, tags: str = ""):
        conn = _db()
        conn.execute(
            "INSERT INTO knowledge (topic, tags, insight, ts) VALUES (?,?,?,datetime('now'))",
            (topic, tags, insight),
        )
        conn.commit()
        conn.close()

    def recall(self, topic: str, limit: int = 5) -> list[str]:
        conn = _db()
        rows = conn.execute(
            """SELECT insight FROM knowledge
               WHERE topic LIKE ? OR tags LIKE ? OR insight LIKE ?
               ORDER BY id DESC LIMIT ?""",
            (f"%{topic}%", f"%{topic}%", f"%{topic}%", limit),
        ).fetchall()
        conn.close()
        return [r["insight"] for r in rows]

    def summarize(self, _unused, topic: str) -> str:
        entries = self.recall(topic, limit=20)
        if not entries:
            return f"No knowledge stored about '{topic}' yet."
        joined = "\n".join(f"- {e}" for e in entries)
        prompt = (
            f"Summarize these market observations about {topic} into 3 key actionable insights:\n"
            f"{joined}"
        )
        return _CLIENT.models.generate_content(model=_MODEL, contents=prompt).text.strip()

    def count(self) -> int:
        conn = _db()
        n = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        conn.close()
        return n


# ── Skill Registry ────────────────────────────────────────────────────────────
class SkillRegistry:
    """
    Full lifecycle for AI-generated skills:
    create → persist → hot-load → track usage → upgrade → version history
    """

    SKILLS_DIR = "skills"

    def __init__(self):
        self._loaded: dict[str, object] = {}
        os.makedirs(self.SKILLS_DIR, exist_ok=True)
        self._restore_from_db()

    # ── persistence ──────────────────────────────────────────────────────────

    def _restore_from_db(self):
        conn = _db()
        rows = conn.execute("SELECT name, path FROM skills").fetchall()
        conn.close()
        restored = 0
        for row in rows:
            try:
                self._hot_load(row["name"], row["path"])
                restored += 1
            except Exception:
                pass
        if restored:
            print(f"[SKILLS] Restored {restored} skill(s) from vault.")

    def _save_to_db(self, name: str, task: str, description: str, path: str, version: int):
        conn = _db()
        conn.execute(
            """INSERT INTO skills (name, task, description, version, path, ts)
               VALUES (?,?,?,?,?,datetime('now'))
               ON CONFLICT(name) DO UPDATE SET
                 task=excluded.task, description=excluded.description,
                 version=excluded.version, path=excluded.path, ts=excluded.ts""",
            (name, task, description, version, path),
        )
        conn.execute(
            "INSERT INTO skill_versions (name, version, path, ts) VALUES (?,?,?,datetime('now'))",
            (name, version, path),
        )
        conn.commit()
        conn.close()

    def _hot_load(self, name: str, path: str) -> object:
        spec   = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        instance = module.Skill()
        self._loaded[name] = instance
        return instance

    # ── code helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _clean_code(raw: str) -> str:
        code = raw.strip()
        if code.startswith("```"):
            code = "\n".join(code.splitlines()[1:])
        if "```" in code:
            code = code[:code.rindex("```")]
        return code.strip()

    @staticmethod
    def _validate_syntax(code: str) -> tuple[bool, str]:
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, str(e)

    def _write_skill(self, name: str, code: str) -> str:
        path = os.path.join(self.SKILLS_DIR, f"{name}.py")
        with open(path, "w") as f:
            f.write(code)
        return path

    # ── public API ───────────────────────────────────────────────────────────

    def create(self, _unused, task: str, name: Optional[str] = None) -> tuple[str, str]:
        """Generate, validate, persist and hot-load a new skill. Returns (name, description)."""
        prompt = textwrap.dedent(f"""
            Write a Python class named 'Skill' with ONE method:
                def execute(self, **kwargs) -> str

            Task: {task}

            Rules:
            - Handle ALL exceptions internally; never raise to caller
            - Return a plain string result
            - No external dependencies beyond stdlib
            - Include a one-line class docstring describing what it does

            Return ONLY valid Python code. No markdown fences.
        """)
        raw  = _CLIENT.models.generate_content(model=_MODEL, contents=prompt).text
        code = self._clean_code(raw)

        ok, err = self._validate_syntax(code)
        if not ok:
            fix_prompt = f"Fix this Python syntax error: {err}\n\nCode:\n{code}\n\nReturn ONLY fixed code."
            code = self._clean_code(
                _CLIENT.models.generate_content(model=_MODEL, contents=fix_prompt).text
            )
            ok, err = self._validate_syntax(code)
            if not ok:
                raise ValueError(f"Syntax error after repair attempt: {err}")

        skill_name = name or f"skill_{int(time.time())}"
        path       = self._write_skill(skill_name, code)
        instance   = self._hot_load(skill_name, path)
        desc       = (instance.__class__.__doc__ or task)[:120].strip()
        self._save_to_db(skill_name, task, desc, path, version=1)
        return skill_name, desc

    def upgrade(self, _unused, name: str, feedback: str = "") -> tuple[str, int]:
        """
        Read existing skill code, ask Gemini to improve it, hot-swap in place.
        Returns (description, new_version).
        """
        conn = _db()
        row  = conn.execute("SELECT task, path, version FROM skills WHERE name=?", (name,)).fetchone()
        conn.close()
        if not row:
            raise KeyError(f"Skill '{name}' not found in registry.")

        with open(row["path"]) as f:
            current_code = f.read()

        default_feedback = "General improvement: better error handling, efficiency, and output quality."
        prompt = textwrap.dedent(f"""
            You are improving an existing Python skill class.

            Original task: {row['task']}
            User feedback / reason for upgrade: {feedback or default_feedback}

            Current code:
            ```python
            {current_code}
            ```

            Rewrite the class with these improvements:
            - Better error handling
            - More informative return strings
            - Efficiency improvements if applicable
            - Fix any bugs evident from the code

            Keep class name 'Skill' and method signature 'execute(self, **kwargs) -> str'.
            Return ONLY valid Python code. No markdown fences.
        """)
        raw  = _CLIENT.models.generate_content(model=_MODEL, contents=prompt).text
        code = self._clean_code(raw)
        ok, err = self._validate_syntax(code)
        if not ok:
            raise ValueError(f"Upgraded code has syntax error: {err}")

        new_version = row["version"] + 1
        path        = self._write_skill(name, code)
        instance    = self._hot_load(name, path)
        desc        = (instance.__class__.__doc__ or row["task"])[:120].strip()
        self._save_to_db(name, row["task"], desc, path, new_version)
        return desc, new_version

    def upgrade_all(self, _unused=None) -> list[str]:
        """Upgrade every registered skill. Returns list of results."""
        conn = _db()
        rows = conn.execute("SELECT name FROM skills").fetchall()
        conn.close()
        results = []
        for row in rows:
            try:
                _, ver = self.upgrade(None, row["name"])
                results.append(f"  ✓ {row['name']} → v{ver}")
            except Exception as e:
                results.append(f"  ✗ {row['name']}: {e}")
        return results

    def execute(self, name: str, **kwargs) -> str:
        if name not in self._loaded:
            raise KeyError(f"Skill '{name}' not loaded.")
        conn = _db()
        try:
            result = str(self._loaded[name].execute(**kwargs))
            conn.execute(
                "UPDATE skills SET usage_count=usage_count+1, success_count=success_count+1 WHERE name=?",
                (name,),
            )
            conn.commit()
            return result
        except Exception as e:
            conn.execute(
                "UPDATE skills SET usage_count=usage_count+1, last_error=? WHERE name=?",
                (str(e), name),
            )
            conn.commit()
            raise
        finally:
            conn.close()

    def info(self, name: str) -> str:
        conn = _db()
        row  = conn.execute("SELECT * FROM skills WHERE name=?", (name,)).fetchone()
        conn.close()
        if not row:
            return f"Skill '{name}' not found."
        sr = f"{row['success_count']}/{row['usage_count']}" if row["usage_count"] else "never run"
        return (
            f"  Name       : {row['name']}\n"
            f"  Version    : v{row['version']}\n"
            f"  Task       : {row['task']}\n"
            f"  Description: {row['description']}\n"
            f"  Success    : {sr}\n"
            f"  Last error : {row['last_error'] or 'none'}\n"
            f"  Created    : {row['ts']}"
        )

    def list_all(self) -> str:
        if not self._loaded:
            return "No skills loaded. Use 'evolve <task>'."
        conn = _db()
        rows = conn.execute(
            "SELECT name, version, usage_count, success_count, description FROM skills"
        ).fetchall()
        conn.close()
        lines = []
        for r in rows:
            status = "●" if r["name"] in self._loaded else "○"
            sr = f"{r['success_count']}/{r['usage_count']}" if r["usage_count"] else "0/0"
            lines.append(f"  {status} {r['name']:30} v{r['version']}  [{sr}]  {r['description'][:40]}")
        return "\n".join(lines)

    def version_history(self, name: str) -> str:
        conn = _db()
        rows = conn.execute(
            "SELECT version, path, ts FROM skill_versions WHERE name=? ORDER BY version",
            (name,),
        ).fetchall()
        conn.close()
        if not rows:
            return f"No version history for '{name}'."
        return "\n".join(f"  v{r['version']}  {r['ts']}  {r['path']}" for r in rows)

    @property
    def names(self) -> list[str]:
        return list(self._loaded.keys())


# ── AI Analyst ────────────────────────────────────────────────────────────────
class AIAnalyst:
    def __init__(self, knowledge: KnowledgeBase, web: "WebIntelligence"):
        self.knowledge = knowledge
        self.web       = web
        self._history: list[types.Content] = []   # persistent multi-turn chat

    def _chat(self, prompt: str) -> str:
        self._history.append(types.Content(role="user", parts=[types.Part(text=prompt)]))
        resp = _CLIENT.models.generate_content(
            model=_MODEL,
            contents=self._history,
        )
        reply = resp.text.strip()
        self._history.append(types.Content(role="model", parts=[types.Part(text=reply)]))
        return reply

    def _generate(self, prompt: str) -> str:
        resp = _CLIENT.models.generate_content(model=_MODEL, contents=prompt)
        return resp.text.strip()

    def analyze(self, data: dict, include_web: bool = True) -> str:
        context = self.knowledge.recall(data["symbol"], limit=3)
        ctx_block = ""
        if context:
            ctx_block = "Past observations:\n" + "\n".join(f"- {c}" for c in context) + "\n\n"

        web_block = ""
        if include_web:
            try:
                snap = self.web.snapshot()
                fg   = snap.get("fear_greed", {})
                gm   = snap.get("global_market", {})
                news = snap.get("news", [])
                web_block = (
                    f"Global market context:\n"
                    f"- Fear & Greed: {fg.get('value','?')} ({fg.get('label','?')})\n"
                    f"- Market cap change 24h: {gm.get('market_cap_change_24h','?')}%\n"
                    f"- BTC dominance: {gm.get('btc_dominance','?')}%\n"
                    f"- Top news: {'; '.join(news[:3])}\n\n"
                )
            except Exception:
                pass

        prompt = (
            f"You are a senior crypto quant analyst with access to real-time global market data.\n\n"
            f"{ctx_block}"
            f"{web_block}"
            f"Technical snapshot:\n{json.dumps(data, indent=2)}\n\n"
            f"Provide structured analysis:\n"
            f"1. Market condition & momentum — cite exact indicator values\n"
            f"2. Macro context — how does global sentiment/dominance affect this asset?\n"
            f"3. Key support/resistance from BB + EMA + VWAP levels\n"
            f"4. Concrete trade plan: entry zone, stop-loss, take-profit targets\n"
            f"5. Confidence score 0-100 and primary risk to the thesis\n"
            f"Be data-driven. No generic statements."
        )
        result = self._chat(prompt)
        self.knowledge.store(
            topic=data["symbol"],
            insight=f"[{data['timeframe']}] price={data['price']} signal={data['signal']} score={data['score']}",
            tags=f"{data['symbol']},analysis",
        )
        return result

    def ask(self, question: str) -> str:
        return self._chat(question)

    def generate_skill_code(self, task: str) -> str:
        prompt = textwrap.dedent(f"""
            Write a Python class named 'Skill' with method 'execute(self, **kwargs) -> str'.
            Task: {task}
            Rules: handle all exceptions, return a plain string, no external deps beyond stdlib.
            Include a one-line class docstring.
            Return ONLY valid Python code. No markdown fences.
        """)
        raw  = self._generate(prompt)
        code = raw.strip()
        if code.startswith("```"):
            code = "\n".join(code.splitlines()[1:])
        if "```" in code:
            code = code[:code.rindex("```")]
        return code.strip()


# ── Paper Trader ──────────────────────────────────────────────────────────────
class PaperTrader:
    def __init__(self, initial_balance: float):
        conn = _db()
        if not conn.execute("SELECT 1 FROM paper_account LIMIT 1").fetchone():
            conn.execute(
                "INSERT INTO paper_account (usdt_balance, ts) VALUES (?, datetime('now'))",
                (initial_balance,),
            )
            conn.commit()
        conn.close()

    def balance(self) -> float:
        conn = _db()
        row  = conn.execute("SELECT usdt_balance FROM paper_account ORDER BY id DESC LIMIT 1").fetchone()
        conn.close()
        return row[0] if row else 0.0

    def trade(self, symbol: str, side: str, usdt_amount: float, price: float) -> str:
        bal = self.balance()
        if side == "BUY":
            if usdt_amount > bal:
                return f"Insufficient paper balance ({bal:.2f} USDT)"
            new_bal    = bal - usdt_amount
            coin_qty   = usdt_amount / price
            msg        = f"BUY {coin_qty:.6f} {symbol} @ {price:.4f} | Cost {usdt_amount:.2f} USDT"
        elif side == "SELL":
            coin_qty   = usdt_amount / price
            new_bal    = bal + usdt_amount
            msg        = f"SELL {coin_qty:.6f} {symbol} @ {price:.4f} | Received {usdt_amount:.2f} USDT"
        else:
            return "Invalid side. Use BUY or SELL."

        conn = _db()
        conn.execute(
            "INSERT INTO paper_account (usdt_balance, ts) VALUES (?, datetime('now'))",
            (new_bal,),
        )
        conn.execute(
            "INSERT INTO paper_trades (symbol, side, amount, price, pnl, ts) VALUES (?,?,?,?,0,datetime('now'))",
            (symbol, side, coin_qty, price),
        )
        conn.commit()
        conn.close()
        return f"[PAPER] {msg} | Balance: {new_bal:.2f} USDT"

    def history(self, limit: int = 10) -> str:
        conn  = _db()
        rows  = conn.execute(
            "SELECT symbol, side, amount, price, ts FROM paper_trades ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        if not rows:
            return "No paper trades yet."
        return "\n".join(
            f"  {r['ts']} | {r['side']:4} {r['amount']:.6f} {r['symbol']} @ {r['price']:.4f}"
            for r in rows
        )


# ── Background Monitor ────────────────────────────────────────────────────────
class PriceMonitor:
    def __init__(self, market: MarketEngine):
        self.market   = market
        self._watches: dict[str, float] = {}
        self._active  = False
        self._prev:   dict[str, float] = {}

    def watch(self, symbol: str, pct: float = 3.0):
        self._watches[symbol] = pct
        if not self._active:
            self._active = True
            threading.Thread(target=self._loop, daemon=True).start()
            print("[MONITOR] Price monitor started.")
        print(f"[MONITOR] Watching {symbol} (±{pct}%)")

    def unwatch(self, symbol: str):
        self._watches.pop(symbol, None)

    def _loop(self):
        while self._active:
            for sym, threshold in list(self._watches.items()):
                try:
                    price = self.market.ticker(sym)["last"]
                    if sym in self._prev:
                        pct = abs(price - self._prev[sym]) / self._prev[sym] * 100
                        if pct >= threshold:
                            msg = f"[ALERT] {sym} moved {pct:.2f}% → {price:.4f}"
                            print(f"\n*** {msg} ***")
                            conn = _db()
                            conn.execute(
                                "INSERT INTO intel (topic,data,ts) VALUES ('alert',?,datetime('now'))",
                                (msg,),
                            )
                            conn.commit()
                            conn.close()
                    self._prev[sym] = price
                except Exception:
                    pass
            time.sleep(60)


# ── Auto-Learning Loop ────────────────────────────────────────────────────────
class LearningLoop:
    """
    Background thread (every 10 min) that:
    1. Fetches global web intel (Fear & Greed, market cap, news)
    2. Scans key markets and stores technical insights
    3. Auto-upgrades skills with low success rates
    4. Logs a full summary to intel DB
    """

    WATCHLIST = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT"]

    def __init__(self, market: MarketEngine, knowledge: KnowledgeBase,
                 skills: SkillRegistry, web: "WebIntelligence"):
        self.market    = market
        self.knowledge = knowledge
        self.skills    = skills
        self.web       = web
        self._active   = False
        self._thread: Optional[threading.Thread] = None
        self.cycles    = 0

    def start(self):
        if self._active:
            return "Auto-learn already running."
        self._active = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return f"Auto-learn started — cycle every {LEARN_INTERVAL}s ({LEARN_INTERVAL//60} min)."

    def stop(self):
        self._active = False
        return "Auto-learn stopped."

    def run_once(self) -> str:
        return self._cycle()

    def _cycle(self) -> str:
        self.cycles += 1
        log = [f"[LEARN] Cycle #{self.cycles} @ {time.strftime('%H:%M:%S')}"]

        # ── 1. Global web intel ───────────────────────────────────────────────
        try:
            snap = self.web.snapshot()
            fg   = snap.get("fear_greed", {})
            gm   = snap.get("global_market", {})
            news = snap.get("news", [])

            if "error" not in fg:
                self.knowledge.store(
                    "GLOBAL",
                    f"Fear&Greed={fg['value']}({fg['label']}) "
                    f"mcap_chg={gm.get('market_cap_change_24h','?')}% "
                    f"btc_dom={gm.get('btc_dominance','?')}%",
                    tags="global,sentiment,auto",
                )
                log.append(f"  Web intel: F&G={fg['value']}({fg['label']}) "
                           f"mkt_chg={gm.get('market_cap_change_24h','?')}%")

            for headline in news[:3]:
                self.knowledge.store("NEWS", headline, tags="news,auto")
            if news:
                log.append(f"  Stored {len(news[:3])} headlines")

            movers = snap.get("top_movers", {})
            if "error" not in movers:
                self.knowledge.store(
                    "MOVERS",
                    f"Gainers: {', '.join(movers.get('gainers',[]))} | "
                    f"Losers: {', '.join(movers.get('losers',[]))}",
                    tags="movers,auto",
                )
        except Exception as e:
            log.append(f"  Web intel error: {e}")

        # ── 2. Technical market scans ─────────────────────────────────────────
        for sym in self.WATCHLIST:
            try:
                data = self.market.full_analysis(sym)
                self.knowledge.store(
                    sym,
                    f"price={data['price']} rsi={data['rsi']} stoch={data['stoch_rsi']} "
                    f"macd={data['macd_hist']} vol={data['vol_ratio']}x "
                    f"signal={data['signal']} score={data['score']}",
                    tags=f"{sym},technical,auto",
                )
                log.append(f"  {sym}: {data['signal']} (score={data['score']:+.2f})")
            except Exception as e:
                log.append(f"  Scan error {sym}: {e}")

        # ── 3. Auto-upgrade weak skills ───────────────────────────────────────
        conn = _db()
        weak = conn.execute(
            """SELECT name FROM skills
               WHERE usage_count >= 3
               AND CAST(success_count AS REAL)/usage_count < 0.6""",
        ).fetchall()
        conn.close()
        for row in weak:
            try:
                _, ver = self.skills.upgrade(
                    None, row["name"],
                    "Low success rate — improve robustness and error handling",
                )
                log.append(f"  Auto-upgraded: {row['name']} → v{ver}")
            except Exception as e:
                log.append(f"  Upgrade failed {row['name']}: {e}")

        # ── 4. Persist summary ────────────────────────────────────────────────
        summary = "\n".join(log)
        conn = _db()
        conn.execute(
            "INSERT INTO intel (topic,data,ts) VALUES ('learn_cycle',?,datetime('now'))",
            (summary,),
        )
        conn.commit()
        conn.close()
        print(f"\n{summary}")
        return summary

    def _loop(self):
        while self._active:
            try:
                self._cycle()
            except Exception as e:
                print(f"[LEARN-ERROR] {e}")
            time.sleep(LEARN_INTERVAL)

    @property
    def status(self) -> str:
        state = "RUNNING" if self._active else "STOPPED"
        kb    = self.knowledge.count()
        return (
            f"Auto-learn : {state}\n"
            f"Cycles     : {self.cycles}\n"
            f"Interval   : {LEARN_INTERVAL}s ({LEARN_INTERVAL//60} min)\n"
            f"Knowledge  : {kb} entries\n"
            f"Watchlist  : {', '.join(self.WATCHLIST)}"
        )


# ── OS Nexus (Authorized Pentest Interface) ───────────────────────────────────
class OSNexus:
    """
    Controlled OS interface for authorized penetration testing.
    - Hard allowlist of permitted tools — nothing outside the list executes
    - No shell=True; args are always passed as a list
    - Every command is logged to intel DB with full timestamp
    - Output is capped to prevent flooding
    - AI script generation shows code for review; never auto-executes
    """

    # Only tools on this list can be called.  Extend deliberately.
    ALLOWED = {
        # network scanners & web testing
        "nmap", "nikto", "gobuster", "ffuf", "sqlmap", "wfuzz",
        # passive recon / OSINT
        "sherlock", "theHarvester", "curl", "wget",
        "dig", "whois", "ping", "traceroute", "host", "nslookup",
        # local network diagnostics
        "netstat", "ss", "ip", "ifconfig", "arp",
        # scripting
        "python3", "python",
    }

    MAX_OUTPUT = 8000   # chars
    TIMEOUT    = 120    # seconds

    def __init__(self):
        self._active: dict[str, subprocess.Popen] = {}
        self._scope: Optional[str] = None          # declared target scope

    # ── Scope gate ────────────────────────────────────────────────────────────
    def declare_scope(self, scope: str) -> str:
        """
        Operator must declare scope before running any tool.
        Example: 'declare 192.168.1.0/24' or 'declare testlab.local'
        """
        self._scope = scope
        self._log("scope_declared", f"Scope set to: {scope}")
        return f"Scope declared: {scope}. Tools are now unlocked for this target."

    def clear_scope(self) -> str:
        self._scope = None
        return "Scope cleared. All pentest tools are locked."

    # ── Logging ───────────────────────────────────────────────────────────────
    def _log(self, topic: str, data: str):
        conn = _db()
        conn.execute(
            "INSERT INTO intel (topic,data,ts) VALUES (?,?,datetime('now'))",
            (f"os_{topic}", data[:4000]),
        )
        conn.commit()
        conn.close()

    # ── Command runner ────────────────────────────────────────────────────────
    def run(self, raw_cmd: str) -> str:
        """
        Execute an allowlisted tool synchronously.
        raw_cmd is split into argv — no shell expansion.
        """
        if not self._scope:
            return (
                "No scope declared. Run:\n"
                "  os declare <target-ip/domain>\n"
                "before using pentest tools."
            )

        argv = shlex.split(raw_cmd)
        if not argv:
            return "Empty command."

        tool = os.path.basename(argv[0]).lower()
        if tool not in self.ALLOWED:
            return (
                f"Tool '{tool}' is not on the allowlist.\n"
                f"Permitted: {', '.join(sorted(self.ALLOWED))}"
            )

        self._log("cmd_start", f"[scope={self._scope}] {raw_cmd}")
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT,
            )
            out = (proc.stdout + proc.stderr).strip()
            out = out[: self.MAX_OUTPUT] + ("…[truncated]" if len(out) > self.MAX_OUTPUT else "")
            self._log("cmd_done", out[:2000])
            return out or "(no output)"
        except subprocess.TimeoutExpired:
            return f"[TIMEOUT] Command exceeded {self.TIMEOUT}s."
        except FileNotFoundError:
            return f"[NOT FOUND] '{argv[0]}' is not installed."
        except Exception as e:
            return f"[ERROR] {e}"

    def run_bg(self, name: str, raw_cmd: str) -> str:
        """Start a long-running tool in the background; output goes to intel DB."""
        if not self._scope:
            return "No scope declared. Run 'os declare <target>' first."
        argv = shlex.split(raw_cmd)
        tool = os.path.basename(argv[0]).lower()
        if tool not in self.ALLOWED:
            return f"Tool '{tool}' not on allowlist."

        def _worker():
            try:
                proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self._active[name] = proc
                out, _ = proc.communicate(timeout=600)
                self._log(f"bg_{name}", out[:4000])
                self._active.pop(name, None)
                print(f"\n[OS-BG] Task '{name}' finished. Check 'intel 3' for output.")
            except Exception as e:
                self._log(f"bg_{name}_error", str(e))

        threading.Thread(target=_worker, daemon=True).start()
        return f"Background task '{name}' started. Use 'intel 3' to see output when done."

    def list_tasks(self) -> str:
        if not self._active:
            return "No background tasks running."
        return "\n".join(f"  • {k}" for k in self._active)

    def kill_task(self, name: str) -> str:
        proc = self._active.pop(name, None)
        if not proc:
            return f"No task named '{name}'."
        proc.terminate()
        return f"Task '{name}' terminated."

    def generate_script(self, task: str) -> str:
        """
        Ask Gemini to write a pentest script for the declared scope.
        Returns the code for HUMAN REVIEW — does NOT execute it.
        """
        if not self._scope:
            return "Declare scope first: os declare <target>"
        prompt = (
            f"Write a Python script for an authorized penetration test against: {self._scope}\n"
            f"Task: {task}\n"
            f"Requirements: use only stdlib + requests, print results, handle errors gracefully.\n"
            f"Return ONLY valid Python code. No markdown fences."
        )
        code = _CLIENT.models.generate_content(model=_MODEL, contents=prompt).text.strip()
        if code.startswith("```"):
            code = "\n".join(code.splitlines()[1:])
        if "```" in code:
            code = code[:code.rindex("```")]
        code = code.strip()

        filename = f"pentest_{int(time.time())}.py"
        with open(filename, "w") as f:
            f.write(code)
        self._log("script_generated", f"file={filename} task={task}")
        return (
            f"Script saved to: {filename}\n"
            f"Review it, then run: os exec python3 {filename}\n\n"
            f"{'─'*50}\n{code}"
        )

    @property
    def status(self) -> str:
        return (
            f"Scope     : {self._scope or 'NOT SET (tools locked)'}\n"
            f"BG Tasks  : {len(self._active)} running\n"
            f"Allowlist : {', '.join(sorted(self.ALLOWED))}"
        )


# ── Core Bot ──────────────────────────────────────────────────────────────────
class MayaTermux:
    def __init__(self):
        _init_db()
        self.market    = MarketEngine(EXCHANGE_ID)
        self.knowledge = KnowledgeBase()
        self.web       = WebIntelligence()
        self.skills    = SkillRegistry()
        self.ai        = AIAnalyst(self.knowledge, self.web)
        self.paper     = PaperTrader(PAPER_BALANCE)
        self.monitor   = PriceMonitor(self.market)
        self.learner   = LearningLoop(self.market, self.knowledge, self.skills, self.web)
        self.os_nexus  = OSNexus()

        print(
            f"\n{'='*60}\n"
            f"  MAYA V14.0  |  EXCHANGE: {EXCHANGE_ID.upper()}\n"
            f"  BOSS: {BOSS_ID}\n"
            f"  PAPER BALANCE : {self.paper.balance():.2f} USDT\n"
            f"  KNOWLEDGE BASE: {self.knowledge.count()} entries\n"
            f"  SKILLS LOADED : {len(self.skills.names)}\n"
            f"  AUTO-LEARN    : every {LEARN_INTERVAL//60} min\n"
            f"{'='*60}\n"
            f"  Type 'help' for commands.\n"
        )

    # ── Command Handlers ──────────────────────────────────────────────────────

    def cmd_scan(self, args):
        symbol    = args[0].upper() if args else "BTC/USDT"
        timeframe = args[1] if len(args) > 1 else "1h"
        try:
            d = self.market.full_analysis(symbol, timeframe)
            conn = _db()
            conn.execute(
                "INSERT INTO intel (topic,data,ts) VALUES ('scan',?,datetime('now'))",
                (json.dumps(d),),
            )
            conn.commit()
            conn.close()
            return (
                f"\n  {d['symbol']} ({d['timeframe']})\n"
                f"  {'─'*40}\n"
                f"  Price      : {d['price']}\n"
                f"  RSI        : {d['rsi']}  |  StochRSI: {d['stoch_rsi']}\n"
                f"  MACD Hist  : {d['macd_hist']}\n"
                f"  EMA 9/21/50: {d['ema9']} / {d['ema21']} / {d['ema50']}\n"
                f"  VWAP       : {d['vwap']}\n"
                f"  BB         : {d['bb_lower']} ── {d['bb_upper']}\n"
                f"  ATR        : {d['atr']}  |  Vol Ratio: {d['vol_ratio']}x\n"
                f"  {'─'*40}\n"
                f"  Score: {d['score']:+.2f}  →  *** {d['signal']} ***"
            )
        except Exception as e:
            return f"Error: {e}"

    def cmd_ai(self, args):
        symbol    = args[0].upper() if args else "BTC/USDT"
        timeframe = args[1] if len(args) > 1 else "1h"
        try:
            data = self.market.full_analysis(symbol, timeframe)
            return f"\n{self.ai.analyze(data)}"
        except Exception as e:
            return f"Error: {e}"

    def cmd_ask(self, args):
        if not args:
            return "Usage: ask <question>"
        return f"\n{self.ai.ask(' '.join(args))}"

    def cmd_multi(self, args):
        symbols = [s.upper() for s in args] if args else ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]
        results, lock = [], threading.Lock()

        def fetch(sym):
            try:
                d = self.market.full_analysis(sym)
                with lock:
                    results.append(
                        f"  {sym:12} | {d['price']:>12.4f} | RSI {d['rsi']:5.1f}"
                        f" | Vol {d['vol_ratio']:.1f}x | {d['signal']}"
                    )
            except Exception as e:
                with lock:
                    results.append(f"  {sym:12} | ERROR: {e}")

        threads = [threading.Thread(target=fetch, args=(s,)) for s in symbols]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return "\nMulti-Scan:\n" + "\n".join(sorted(results))

    def cmd_buy(self, args):
        if len(args) < 2:
            return "Usage: buy <SYMBOL> <USDT>"
        try:
            price = self.market.ticker(args[0].upper())["last"]
            return self.paper.trade(args[0].upper(), "BUY", float(args[1]), price)
        except Exception as e:
            return f"Error: {e}"

    def cmd_sell(self, args):
        if len(args) < 2:
            return "Usage: sell <SYMBOL> <USDT>"
        try:
            price = self.market.ticker(args[0].upper())["last"]
            return self.paper.trade(args[0].upper(), "SELL", float(args[1]), price)
        except Exception as e:
            return f"Error: {e}"

    def cmd_balance(self, _):
        return f"Paper Balance: {self.paper.balance():.4f} USDT"

    def cmd_trades(self, args):
        limit = int(args[0]) if args else 10
        return f"Last {limit} trades:\n{self.paper.history(limit)}"

    def cmd_watch(self, args):
        if not args:
            return "Usage: watch <SYMBOL> [pct]"
        self.monitor.watch(args[0].upper(), float(args[1]) if len(args) > 1 else 3.0)
        return f"Monitoring {args[0].upper()}."

    def cmd_unwatch(self, args):
        if not args:
            return "Usage: unwatch <SYMBOL>"
        self.monitor.unwatch(args[0].upper())
        return f"Stopped watching {args[0].upper()}."

    # ── Evolution / Skill Commands ────────────────────────────────────────────

    def cmd_evolve(self, args):
        if not args:
            return "Usage: evolve <task description>"
        task = " ".join(args)
        print(f"[EVOLUTION] Generating skill for: {task}")
        try:
            name, desc = self.skills.create(None, task)
            return f"Skill created: {name}\nDescription : {desc}"
        except Exception as e:
            return f"Evolution failed: {e}"

    def cmd_upgrade(self, args):
        if not args:
            return "Usage: upgrade <skill_name|all> [feedback]"
        target   = args[0]
        feedback = " ".join(args[1:]) if len(args) > 1 else ""
        if target == "all":
            results = self.skills.upgrade_all()
            return "Self-Upgrade Results:\n" + "\n".join(results)
        try:
            desc, ver = self.skills.upgrade(None, target, feedback)
            return f"Upgraded '{target}' to v{ver}\nDescription: {desc}"
        except Exception as e:
            return f"Upgrade failed: {e}"

    def cmd_skills(self, _):
        return f"Skills Registry:\n{self.skills.list_all()}"

    def cmd_skill_info(self, args):
        if not args:
            return "Usage: skill <skill_name>"
        return self.skills.info(args[0])

    def cmd_versions(self, args):
        if not args:
            return "Usage: versions <skill_name>"
        return self.skills.version_history(args[0])

    def cmd_run(self, args):
        if not args:
            return "Usage: run <skill_name> [key=value ...]"
        name   = args[0]
        kwargs = {}
        for token in args[1:]:
            if "=" in token:
                k, v = token.split("=", 1)
                kwargs[k] = v
        try:
            return self.skills.execute(name, **kwargs)
        except Exception as e:
            return f"Error: {e}"

    # ── Knowledge Commands ────────────────────────────────────────────────────

    def cmd_learn(self, args):
        if not args:
            return "Usage: learn <insight>"
        insight = " ".join(args)
        self.knowledge.store("manual", insight, tags="manual")
        return f"Stored in knowledge base ({self.knowledge.count()} total entries)."

    def cmd_recall(self, args):
        if not args:
            return "Usage: recall <topic>"
        topic   = " ".join(args)
        entries = self.knowledge.recall(topic, limit=8)
        if not entries:
            return f"No knowledge found for '{topic}'."
        lines = [f"  {i+1}. {e}" for i, e in enumerate(entries)]
        return f"Knowledge on '{topic}':\n" + "\n".join(lines)

    def cmd_summarize(self, args):
        topic = " ".join(args) if args else "BTC"
        return f"\n{self.knowledge.summarize(None, topic)}"

    # ── Learning Loop Commands ────────────────────────────────────────────────

    def cmd_autolearn(self, args):
        verb = args[0].lower() if args else "status"
        if verb == "on":
            return self.learner.start()
        if verb == "off":
            return self.learner.stop()
        if verb == "now":
            return self.learner.run_once()
        return self.learner.status

    # ── Intel ─────────────────────────────────────────────────────────────────

    def cmd_intel(self, args):
        limit = int(args[0]) if args else 5
        conn  = _db()
        rows  = conn.execute(
            "SELECT topic, data, ts FROM intel ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        if not rows:
            return "No intel logged yet."
        return "\n".join(f"  [{r['ts']}] {r['topic']}: {r['data'][:90]}..." for r in rows)

    def cmd_recon(self, args) -> str:
        """Passive DNS + geolocation recon on a domain or IP (requires declared scope)."""
        if not args:
            return "Usage: recon <domain | ip>"
        target = args[0]
        if not self.os_nexus._scope:
            return "Declare scope first: os declare <target>"

        lines = [f"Recon: {target}"]

        # DNS lookup
        dns = self.os_nexus.run(f"dig +short {target}")
        lines.append(f"DNS  : {dns.strip() or '(no result)'}")

        # Reverse / WHOIS summary
        whois_out = self.os_nexus.run(f"whois {target}")
        # Extract only the most useful WHOIS lines
        useful = [
            ln for ln in whois_out.splitlines()
            if any(k in ln.lower() for k in ("registrar", "country", "org", "netname", "cidr", "created", "expir"))
        ]
        lines.append("WHOIS:\n" + "\n".join(f"  {ln.strip()}" for ln in useful[:10]))

        # IP geolocation (public, no-auth API)
        ip = dns.strip().splitlines()[0] if dns.strip() else target
        try:
            geo = _SESSION.get(f"https://ip-api.com/json/{ip}?fields=status,city,regionName,country,isp,org,as", timeout=6).json()
            if geo.get("status") == "success":
                lines.append(
                    f"Geo  : {geo.get('city')}, {geo.get('regionName')}, {geo.get('country')}\n"
                    f"ISP  : {geo.get('isp')} | {geo.get('org')}\n"
                    f"ASN  : {geo.get('as')}"
                )
        except Exception:
            pass

        result = "\n".join(lines)
        self._log("recon", result)
        return result

    def cmd_social(self, args) -> str:
        """OSINT: find public accounts for a username across platforms (sherlock)."""
        if not args:
            return "Usage: social <username>"
        username = args[0]
        if not self.os_nexus._scope:
            return (
                "Declare scope first.\n"
                "Example: os declare <username> (confirms you have authorization to research this person)"
            )
        print(f"[OSINT] Running sherlock on: {username} (this may take 30–60s)...")
        result = self.os_nexus.run(f"sherlock {username} --timeout 10 --print-found")
        self._log("social_osint", f"username={username}\n{result[:2000]}")
        return result or "No results or sherlock not installed. Run: pip install sherlock-project"

    def cmd_os(self, args) -> str:
        """Route all 'os' sub-commands to OSNexus."""
        if not args:
            return self.os_nexus.status
        sub = args[0].lower()
        rest = args[1:]

        if sub == "declare":
            if not rest:
                return "Usage: os declare <target-ip/domain/CIDR>"
            return self.os_nexus.declare_scope(" ".join(rest))

        if sub == "clear":
            return self.os_nexus.clear_scope()

        if sub in ("exec", "run"):
            if not rest:
                return "Usage: os exec <tool> [args...]"
            return self.os_nexus.run(" ".join(rest))

        if sub == "bg":
            if len(rest) < 2:
                return "Usage: os bg <task-name> <tool> [args...]"
            return self.os_nexus.run_bg(rest[0], " ".join(rest[1:]))

        if sub == "tasks":
            return self.os_nexus.list_tasks()

        if sub == "kill":
            if not rest:
                return "Usage: os kill <task-name>"
            return self.os_nexus.kill_task(rest[0])

        if sub == "script":
            if not rest:
                return "Usage: os script <task description>"
            return self.os_nexus.generate_script(" ".join(rest))

        if sub == "status":
            return self.os_nexus.status

        return (
            "OS sub-commands:\n"
            "  os declare <target>         set authorized scope\n"
            "  os clear                    clear scope (lock tools)\n"
            "  os exec <tool> [args]       run allowlisted tool\n"
            "  os bg <name> <tool> [args]  run tool in background\n"
            "  os tasks                    list background tasks\n"
            "  os kill <name>              stop background task\n"
            "  os script <task>            generate pentest script (review only)\n"
            "  os status                   show scope + allowlist"
        )

    def cmd_webintel(self, args):
        """Fetch and display live global web intelligence snapshot."""
        section = args[0].lower() if args else "all"
        try:
            if section == "news":
                return "\n  ".join(["Headlines:"] + self.web.news(10))
            if section == "fear":
                fg = self.web.fear_greed()
                return (
                    f"  Fear & Greed : {fg.get('value')} ({fg.get('label')})\n"
                    f"  Yesterday    : {fg.get('yesterday')}\n"
                    f"  Last week    : {fg.get('last_week')}"
                )
            if section == "market":
                gm = self.web.global_market()
                return json.dumps(gm, indent=2)
            if section == "movers":
                mv = self.web.top_movers()
                return (
                    f"  Gainers: {', '.join(mv.get('gainers', []))}\n"
                    f"  Losers : {', '.join(mv.get('losers', []))}"
                )
            if section == "mempool":
                return json.dumps(self.web.btc_mempool(), indent=2)
            # default: full snapshot
            snap = self.web.snapshot()
            return self.web.format_snapshot(snap)
        except Exception as e:
            return f"Error fetching web intel: {e}"

    # ── Dispatcher ────────────────────────────────────────────────────────────

    HELP = """
━━ MARKET ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  scan    [SYMBOL] [tf]       technical analysis snapshot
  ai      [SYMBOL] [tf]       deep Gemini AI analysis
  ask     <question>          free-form AI question
  multi   [S1 S2 ...]         parallel multi-symbol scan

━━ TRADING (PAPER) ──────────────────────────────────────
  buy     <SYMBOL> <USDT>     paper buy
  sell    <SYMBOL> <USDT>     paper sell
  balance                     paper account balance
  trades  [n]                 last n paper trades

━━ GLOBAL INTERNET ──────────────────────────────────────
  webintel [all|fear|market|movers|news|mempool]
                              live global crypto intel

━━ PASSIVE RECON / OSINT ────────────────────────────────
  recon  <domain|ip>          DNS + WHOIS + geolocation (scope required)
  social <username>           find public accounts via sherlock (scope required)

━━ OS NEXUS (AUTHORIZED PENTEST) ────────────────────────
  os declare <target>         set authorized scope (required first)
  os exec <tool> [args]       run allowlisted tool (nmap, sqlmap, etc.)
  os bg <name> <tool> [args]  run tool in background
  os tasks / kill <name>      manage background tasks
  os script <description>     AI writes script → saved for review
  os clear / status           manage scope

━━ MONITORING ───────────────────────────────────────────
  watch   <SYMBOL> [pct]      alert on ±pct% price move
  unwatch <SYMBOL>            stop monitoring

━━ SELF-EVOLUTION ───────────────────────────────────────
  evolve  <task>              generate & load new skill
  upgrade <name|all> [why]    improve skill(s) via AI
  skills                      list all skills with stats
  skill   <name>              skill detail & performance
  versions <name>             skill version history
  run     <name> [k=v ...]    execute a skill

━━ KNOWLEDGE & LEARNING ─────────────────────────────────
  learn   <insight>           manually store knowledge
  recall  <topic>             recall past observations
  summarize [topic]           AI summary of knowledge
  autolearn on|off|now|status toggle background learning

━━ SYSTEM ───────────────────────────────────────────────
  intel   [n]                 last n logged intel entries
  help                        this message
  exit                        quit
"""

    def handle_boss(self, uid: str, raw: str) -> str:
        if uid != BOSS_ID:
            return "UNAUTHORIZED"
        parts = raw.strip().split()
        if not parts:
            return ""
        verb, args = parts[0].lower(), parts[1:]
        dispatch = {
            "scan":      self.cmd_scan,
            "ai":        self.cmd_ai,
            "ask":       self.cmd_ask,
            "multi":     self.cmd_multi,
            "buy":       self.cmd_buy,
            "sell":      self.cmd_sell,
            "balance":   self.cmd_balance,
            "trades":    self.cmd_trades,
            "watch":     self.cmd_watch,
            "unwatch":   self.cmd_unwatch,
            "evolve":    self.cmd_evolve,
            "upgrade":   self.cmd_upgrade,
            "skills":    self.cmd_skills,
            "skill":     self.cmd_skill_info,
            "versions":  self.cmd_versions,
            "run":       self.cmd_run,
            "learn":     self.cmd_learn,
            "recall":    self.cmd_recall,
            "summarize": self.cmd_summarize,
            "autolearn": self.cmd_autolearn,
            "intel":     self.cmd_intel,
            "os":        self.cmd_os,
            "recon":     self.cmd_recon,
            "social":    self.cmd_social,
            "webintel":  self.cmd_webintel,
            "help":      lambda _: self.HELP,
            "?":         lambda _: self.HELP,
        }
        handler = dispatch.get(verb)
        if handler:
            return handler(args)
        return f"Unknown command '{verb}'. Type 'help'."


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    maya = MayaTermux()
    while True:
        try:
            uid = input("[ID]: ").strip()
            if not uid:
                continue
            cmd = input(f"[{uid}] > ").strip()
            if cmd.lower() == "exit":
                print("Shutting down. Goodbye.")
                break
            print(f"\nMAYA: {maya.handle_boss(uid, cmd)}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nShutting down.")
            break
