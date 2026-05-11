"""
MayaTermux V10.0 — AI-Powered Crypto Trading Intelligence
"""
import os
import time
import sqlite3
import threading
import importlib.util
import json
from datetime import datetime, timezone
from typing import Optional

import ccxt
import pandas as pd
import google.generativeai as genai

# ── Config ────────────────────────────────────────────────────────────────────
BOSS_ID       = os.environ.get("BOSS_ID", "SUPREME_BOSS_01")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
EXCHANGE_ID   = os.environ.get("EXCHANGE_ID", "binance")      # any ccxt exchange
PAPER_BALANCE  = float(os.environ.get("PAPER_BALANCE", "10000"))  # USDT

if not GEMINI_API_KEY:
    raise EnvironmentError("Set GEMINI_API_KEY environment variable before running.")

genai.configure(api_key=GEMINI_API_KEY)


# ── Technical Indicators ──────────────────────────────────────────────────────
class Indicators:
    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / loss.replace(0, float("nan"))
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(series: pd.Series, fast=12, slow=26, signal=9):
        ema_fast   = series.ewm(span=fast, adjust=False).mean()
        ema_slow   = series.ewm(span=slow, adjust=False).mean()
        macd_line  = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram  = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger(series: pd.Series, period=20, std_dev=2):
        sma   = series.rolling(period).mean()
        std   = series.rolling(period).std()
        upper = sma + std_dev * std
        lower = sma - std_dev * std
        return upper, sma, lower

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low   = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close  = (df["low"]  - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean()


# ── Paper Trading Engine ──────────────────────────────────────────────────────
class PaperTrader:
    def __init__(self, db_path: str, initial_balance: float):
        self.db_path = db_path
        self._init(initial_balance)

    def _init(self, initial_balance: float):
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS paper_account (
                id INTEGER PRIMARY KEY,
                usdt_balance REAL,
                ts TEXT
            );
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                side TEXT,
                amount REAL,
                price REAL,
                pnl REAL,
                ts TEXT
            );
        """)
        # Seed balance only once
        if not conn.execute("SELECT 1 FROM paper_account LIMIT 1").fetchone():
            conn.execute(
                "INSERT INTO paper_account (usdt_balance, ts) VALUES (?, datetime('now'))",
                (initial_balance,),
            )
        conn.commit()
        conn.close()

    def balance(self) -> float:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT usdt_balance FROM paper_account ORDER BY id DESC LIMIT 1").fetchone()
        conn.close()
        return row[0] if row else 0.0

    def trade(self, symbol: str, side: str, usdt_amount: float, price: float) -> str:
        bal = self.balance()
        if side == "BUY":
            if usdt_amount > bal:
                return f"Insufficient paper balance ({bal:.2f} USDT)"
            new_bal = bal - usdt_amount
            coin_amount = usdt_amount / price
            pnl = 0.0
            msg = f"BUY {coin_amount:.6f} {symbol} @ {price:.2f} | Cost: {usdt_amount:.2f} USDT"
        elif side == "SELL":
            coin_amount = usdt_amount / price
            pnl = usdt_amount - usdt_amount  # flat for now; real PnL needs position tracking
            new_bal = bal + usdt_amount
            msg = f"SELL {coin_amount:.6f} {symbol} @ {price:.2f} | Received: {usdt_amount:.2f} USDT"
        else:
            return "Invalid side. Use BUY or SELL."

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO paper_account (usdt_balance, ts) VALUES (?, datetime('now'))",
            (new_bal,),
        )
        conn.execute(
            "INSERT INTO paper_trades (symbol, side, amount, price, pnl, ts) VALUES (?,?,?,?,?,datetime('now'))",
            (symbol, side, coin_amount, price, pnl),
        )
        conn.commit()
        conn.close()
        return f"[PAPER TRADE] {msg} | New Balance: {new_bal:.2f} USDT"

    def history(self, limit: int = 10) -> str:
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT symbol, side, amount, price, ts FROM paper_trades ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        if not rows:
            return "No paper trades yet."
        lines = [f"  {r[4]} | {r[1]:4} {r[2]:.6f} {r[0]} @ {r[3]:.2f}" for r in rows]
        return "\n".join(lines)


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
        df = self.ohlcv(symbol, timeframe, limit=100)
        close = df["close"]

        rsi_val   = Indicators.rsi(close).iloc[-1]
        macd_line, sig_line, hist = Indicators.macd(close)
        bb_upper, bb_mid, bb_lower = Indicators.bollinger(close)
        atr_val   = Indicators.atr(df).iloc[-1]
        ema9      = Indicators.ema(close, 9).iloc[-1]
        ema21     = Indicators.ema(close, 21).iloc[-1]
        price     = close.iloc[-1]

        # Simple signal score (-1 to +1 scale)
        signals = []
        signals.append(1  if rsi_val < 30 else (-1 if rsi_val > 70 else 0))
        signals.append(1  if hist.iloc[-1] > 0 else -1)
        signals.append(1  if ema9 > ema21 else -1)
        signals.append(1  if price > bb_mid.iloc[-1] else -1)
        score = sum(signals) / len(signals)

        return {
            "symbol":    symbol,
            "timeframe": timeframe,
            "price":     round(price, 4),
            "rsi":       round(rsi_val, 2),
            "macd_hist": round(hist.iloc[-1], 4),
            "ema9":      round(ema9, 4),
            "ema21":     round(ema21, 4),
            "bb_upper":  round(bb_upper.iloc[-1], 4),
            "bb_lower":  round(bb_lower.iloc[-1], 4),
            "atr":       round(atr_val, 4),
            "score":     round(score, 2),
            "signal":    "STRONG BUY" if score >= 0.75 else
                         "BUY"        if score >= 0.25 else
                         "SELL"       if score <= -0.25 else
                         "STRONG SELL" if score <= -0.75 else "NEUTRAL",
        }


# ── AI Analyst ───────────────────────────────────────────────────────────────
class AIAnalyst:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-pro")
        self.chat  = self.model.start_chat(history=[])

    def analyze(self, data: dict) -> str:
        prompt = (
            f"You are a senior crypto quant analyst. Given this market snapshot:\n"
            f"{json.dumps(data, indent=2)}\n\n"
            f"Give a concise 3-paragraph analysis:\n"
            f"1. Current market condition & momentum\n"
            f"2. Key risk factors and support/resistance zones based on indicators\n"
            f"3. Actionable recommendation with stop-loss and take-profit levels.\n"
            f"Be specific and data-driven. No fluff."
        )
        response = self.chat.send_message(prompt)
        return response.text.strip()

    def ask(self, question: str) -> str:
        response = self.chat.send_message(question)
        return response.text.strip()

    def generate_skill(self, task: str) -> str:
        prompt = (
            f"Write a Python class named 'Skill' with a single method 'execute(self, **kwargs) -> str' "
            f"that accomplishes: {task}\n"
            f"Requirements: handle exceptions, return a string result.\n"
            f"Return ONLY valid Python code. No markdown fences."
        )
        response = self.model.generate_content(prompt)
        code = response.text.strip()
        if code.startswith("```"):
            code = "\n".join(code.splitlines()[1:])
        if "```" in code:
            code = code[:code.rindex("```")]
        return code.strip()


# ── Background Monitor ────────────────────────────────────────────────────────
class Monitor:
    def __init__(self, market: MarketEngine, db_path: str):
        self.market   = market
        self.db_path  = db_path
        self._active  = False
        self._watches: dict[str, float] = {}  # symbol -> alert threshold
        self._thread: Optional[threading.Thread] = None

    def watch(self, symbol: str, pct_change: float = 3.0):
        self._watches[symbol] = pct_change
        if not self._active:
            self._active = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            print(f"[MONITOR] Background monitor started.")
        print(f"[MONITOR] Watching {symbol} (alert at ±{pct_change}% move)")

    def unwatch(self, symbol: str):
        self._watches.pop(symbol, None)
        if not self._watches:
            self._active = False
        print(f"[MONITOR] Stopped watching {symbol}")

    def _log(self, msg: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO intel (topic, data, ts) VALUES (?, ?, datetime('now'))",
            ("monitor_alert", msg),
        )
        conn.commit()
        conn.close()
        print(f"\n*** [ALERT] {msg} ***")

    def _loop(self):
        prev_prices: dict[str, float] = {}
        while self._active:
            for symbol, threshold in list(self._watches.items()):
                try:
                    t = self.market.ticker(symbol)
                    price = t["last"]
                    if symbol in prev_prices:
                        pct = abs(price - prev_prices[symbol]) / prev_prices[symbol] * 100
                        if pct >= threshold:
                            self._log(f"{symbol} moved {pct:.2f}% to {price:.4f}")
                    prev_prices[symbol] = price
                except Exception:
                    pass
            time.sleep(60)


# ── Core Bot ──────────────────────────────────────────────────────────────────
class MayaTermux:
    def __init__(self):
        self.db_path = "maya_vault.db"
        self._init_db()
        self.market   = MarketEngine(EXCHANGE_ID)
        self.paper    = PaperTrader(self.db_path, PAPER_BALANCE)
        self.ai       = AIAnalyst()
        self.monitor  = Monitor(self.market, self.db_path)
        self._skills: dict[str, object] = {}

        print(
            f"\n{'='*55}\n"
            f"  MAYA V10.0  |  EXCHANGE: {EXCHANGE_ID.upper()}\n"
            f"  BOSS: {BOSS_ID}  |  PAPER BALANCE: {self.paper.balance():.2f} USDT\n"
            f"{'='*55}\n"
            f"  Type 'help' for commands.\n"
        )

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS intel (id INTEGER PRIMARY KEY, topic TEXT, data TEXT, ts TEXT);
            CREATE TABLE IF NOT EXISTS skills (id INTEGER PRIMARY KEY, name TEXT, path TEXT, ts TEXT);
        """)
        conn.commit()
        conn.close()

    def _log(self, topic: str, data: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO intel (topic, data, ts) VALUES (?, ?, datetime('now'))",
            (topic, data),
        )
        conn.commit()
        conn.close()

    # ── Commands ──────────────────────────────────────────────────────────────

    def cmd_scan(self, args: list[str]) -> str:
        symbol    = args[0].upper() if args else "BTC/USDT"
        timeframe = args[1] if len(args) > 1 else "1h"
        try:
            data = self.market.full_analysis(symbol, timeframe)
            self._log("scan", json.dumps(data))
            return (
                f"\n  Symbol   : {data['symbol']} ({data['timeframe']})\n"
                f"  Price    : {data['price']}\n"
                f"  RSI      : {data['rsi']}\n"
                f"  MACD Hist: {data['macd_hist']}\n"
                f"  EMA 9/21 : {data['ema9']} / {data['ema21']}\n"
                f"  BB       : {data['bb_lower']} — {data['bb_upper']}\n"
                f"  ATR      : {data['atr']}\n"
                f"  Score    : {data['score']}  →  {data['signal']}"
            )
        except Exception as e:
            return f"Error: {e}"

    def cmd_ai(self, args: list[str]) -> str:
        symbol    = args[0].upper() if args else "BTC/USDT"
        timeframe = args[1] if len(args) > 1 else "1h"
        try:
            data     = self.market.full_analysis(symbol, timeframe)
            analysis = self.ai.analyze(data)
            self._log("ai_analysis", analysis)
            return f"\n{analysis}"
        except Exception as e:
            return f"Error: {e}"

    def cmd_ask(self, args: list[str]) -> str:
        if not args:
            return "Usage: ask <question>"
        question = " ".join(args)
        try:
            return f"\n{self.ai.ask(question)}"
        except Exception as e:
            return f"Error: {e}"

    def cmd_buy(self, args: list[str]) -> str:
        if len(args) < 2:
            return "Usage: buy <SYMBOL> <USDT amount>"
        symbol, amount = args[0].upper(), float(args[1])
        try:
            price = self.market.ticker(symbol)["last"]
            return self.paper.trade(symbol, "BUY", amount, price)
        except Exception as e:
            return f"Error: {e}"

    def cmd_sell(self, args: list[str]) -> str:
        if len(args) < 2:
            return "Usage: sell <SYMBOL> <USDT amount>"
        symbol, amount = args[0].upper(), float(args[1])
        try:
            price = self.market.ticker(symbol)["last"]
            return self.paper.trade(symbol, "SELL", amount, price)
        except Exception as e:
            return f"Error: {e}"

    def cmd_balance(self, _) -> str:
        return f"Paper Balance: {self.paper.balance():.4f} USDT"

    def cmd_trades(self, args: list[str]) -> str:
        limit = int(args[0]) if args else 10
        return f"Last {limit} trades:\n{self.paper.history(limit)}"

    def cmd_watch(self, args: list[str]) -> str:
        if not args:
            return "Usage: watch <SYMBOL> [pct_threshold]"
        symbol    = args[0].upper()
        threshold = float(args[1]) if len(args) > 1 else 3.0
        self.monitor.watch(symbol, threshold)
        return f"Monitoring {symbol} (alert at ±{threshold}% move)."

    def cmd_unwatch(self, args: list[str]) -> str:
        if not args:
            return "Usage: unwatch <SYMBOL>"
        self.monitor.unwatch(args[0].upper())
        return f"Stopped watching {args[0].upper()}."

    def cmd_evolve(self, args: list[str]) -> str:
        if not args:
            return "Usage: evolve <task description>"
        task = " ".join(args)
        print(f"[EVOLUTION] Generating skill: {task}")
        try:
            code       = self.ai.generate_skill(task)
            skill_name = f"skill_{int(time.time())}"
            path       = os.path.join("skills", f"{skill_name}.py")
            os.makedirs("skills", exist_ok=True)
            with open(path, "w") as f:
                f.write(code)
            spec   = importlib.util.spec_from_file_location(skill_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._skills[skill_name] = module.Skill()
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT INTO skills (name, path, ts) VALUES (?, ?, datetime('now'))",
                (skill_name, path),
            )
            conn.commit()
            conn.close()
            return f"Skill '{skill_name}' integrated and ready."
        except Exception as e:
            return f"Evolution failed: {e}"

    def cmd_skills(self, _) -> str:
        if not self._skills:
            return "No skills loaded yet. Use 'evolve <task>'."
        return "Loaded skills:\n" + "\n".join(f"  • {k}" for k in self._skills)

    def cmd_run(self, args: list[str]) -> str:
        if not args:
            return "Usage: run <skill_name> [key=value ...]"
        name = args[0]
        if name not in self._skills:
            return f"Skill '{name}' not found. Use 'skills' to list."
        kwargs = {}
        for token in args[1:]:
            if "=" in token:
                k, v = token.split("=", 1)
                kwargs[k] = v
        try:
            return str(self._skills[name].execute(**kwargs))
        except Exception as e:
            return f"Skill error: {e}"

    def cmd_intel(self, args: list[str]) -> str:
        limit = int(args[0]) if args else 5
        conn  = sqlite3.connect(self.db_path)
        rows  = conn.execute(
            "SELECT topic, data, ts FROM intel ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        if not rows:
            return "No intel logged yet."
        lines = [f"  [{r[2]}] {r[0]}: {r[1][:80]}..." for r in rows]
        return "\n".join(lines)

    def cmd_multi(self, args: list[str]) -> str:
        symbols   = args if args else ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        results   = []
        lock      = threading.Lock()

        def fetch(sym):
            try:
                data = self.market.full_analysis(sym)
                with lock:
                    results.append(f"  {sym:12} | {data['price']:>12.4f} | RSI {data['rsi']:5.1f} | {data['signal']}")
            except Exception as e:
                with lock:
                    results.append(f"  {sym:12} | ERROR: {e}")

        threads = [threading.Thread(target=fetch, args=(s.upper(),)) for s in symbols]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return "\nMulti-Scan Results:\n" + "\n".join(sorted(results))

    # ── Dispatcher ───────────────────────────────────────────────────────────

    HELP = """
Commands:
  scan   [SYMBOL] [tf]      — technical analysis (default BTC/USDT 1h)
  ai     [SYMBOL] [tf]      — deep AI analysis via Gemini
  ask    <question>         — free-form AI question
  multi  [S1 S2 S3...]      — scan multiple symbols in parallel
  buy    <SYMBOL> <USDT>    — paper buy
  sell   <SYMBOL> <USDT>    — paper sell
  balance                   — show paper account balance
  trades [n]                — last n paper trades
  watch  <SYMBOL> [pct]     — alert on % price move (background)
  unwatch <SYMBOL>          — stop monitoring
  evolve <task>             — generate & load a new AI skill
  skills                    — list loaded skills
  run    <skill> [k=v ...]  — execute a loaded skill
  intel  [n]                — show last n logged intel entries
  help                      — this message
  exit                      — quit
"""

    def handle_boss(self, uid: str, raw_cmd: str) -> str:
        if uid != BOSS_ID:
            return "UNAUTHORIZED"

        parts = raw_cmd.strip().split()
        if not parts:
            return ""
        verb, args = parts[0].lower(), parts[1:]

        dispatch = {
            "scan":    self.cmd_scan,
            "ai":      self.cmd_ai,
            "ask":     self.cmd_ask,
            "multi":   self.cmd_multi,
            "buy":     self.cmd_buy,
            "sell":    self.cmd_sell,
            "balance": self.cmd_balance,
            "trades":  self.cmd_trades,
            "watch":   self.cmd_watch,
            "unwatch": self.cmd_unwatch,
            "evolve":  self.cmd_evolve,
            "skills":  self.cmd_skills,
            "run":     self.cmd_run,
            "intel":   self.cmd_intel,
            "help":    lambda _: self.HELP,
            "?":       lambda _: self.HELP,
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
            result = maya.handle_boss(uid, cmd)
            print(f"\nMAYA: {result}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nShutting down.")
            break
