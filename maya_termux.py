import os
import time
import sqlite3
import threading
import importlib.util

import ccxt
import pandas as pd
import google.generativeai as genai

BOSS_ID = os.environ.get("BOSS_ID", "SUPREME_BOSS_01")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    raise EnvironmentError("Set GEMINI_API_KEY environment variable before running.")

genai.configure(api_key=GEMINI_API_KEY)


class MayaTermux:
    def __init__(self):
        self.db_path = "maya_vault.db"
        self._init_db()
        print(f"MAYA V9.1: [TERMUX MODE ONLINE] [BOSS: {BOSS_ID}]")

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS intel (id INTEGER PRIMARY KEY, topic TEXT, data TEXT, ts TEXT);
            CREATE TABLE IF NOT EXISTS skills (id INTEGER PRIMARY KEY, name TEXT, path TEXT, ts TEXT);
        """)
        conn.commit()
        conn.close()

    def _log_intel(self, topic: str, data: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO intel (topic, data, ts) VALUES (?, ?, datetime('now'))",
            (topic, data),
        )
        conn.commit()
        conn.close()

    def _register_skill(self, name: str, path: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO skills (name, path, ts) VALUES (?, ?, datetime('now'))",
            (name, path),
        )
        conn.commit()
        conn.close()

    def self_evolve(self, task: str):
        """Generates a new Python skill module via Gemini and hot-loads it."""
        print(f"[EVOLUTION] Learning: {task}")
        model = genai.GenerativeModel("gemini-1.5-pro")
        prompt = (
            f"Write a clean Python class named 'Skill' with a single 'execute' method "
            f"that accomplishes: {task}. Return ONLY valid Python code, no markdown."
        )
        response = model.generate_content(prompt)
        code = response.text.strip()
        if code.startswith("```"):
            code = "\n".join(code.splitlines()[1:])
        if code.endswith("```"):
            code = "\n".join(code.splitlines()[:-1])

        skill_name = f"skill_{int(time.time())}"
        path = os.path.join("skills", f"{skill_name}.py")
        os.makedirs("skills", exist_ok=True)

        with open(path, "w") as f:
            f.write(code)

        # Hot-load the module to validate it parses correctly
        spec = importlib.util.spec_from_file_location(skill_name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self._register_skill(skill_name, path)
        print(f"[EVOLUTION] New skill integrated: {skill_name}")
        return skill_name

    def market_scan(self, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 50):
        """Fetches OHLCV data from Binance and reports trend."""
        print(f"[MARKET] Scanning {symbol} ({timeframe})...")
        try:
            exchange = ccxt.binance()
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
            last_price = df["close"].iloc[-1]
            avg_price = df["close"].mean()
            trend = "BULLISH" if last_price > avg_price else "BEARISH"
            report = f"{symbol} @ {last_price:.2f} USDT | Trend: {trend}"
            print(f"[MARKET] {report}")
            self._log_intel("market_scan", report)
            return report
        except Exception as e:
            print(f"[MARKET-ERROR] {e}")
            return f"Error: {e}"

    def handle_boss(self, uid: str, cmd: str) -> str:
        if uid != BOSS_ID:
            return "UNAUTHORIZED"

        cmd_lower = cmd.lower()

        if cmd_lower.startswith("evolve "):
            task = cmd[7:].strip()
            if not task:
                return "Usage: evolve <task description>"
            skill_name = self.self_evolve(task)
            return f"Evolution complete. Skill: {skill_name}"

        if cmd_lower.startswith("market"):
            parts = cmd.split()
            symbol = parts[1].upper() if len(parts) > 1 else "BTC/USDT"
            return self.market_scan(symbol)

        if cmd_lower in ("help", "?"):
            return (
                "Commands:\n"
                "  evolve <task>      — generate and load a new skill module\n"
                "  market [SYMBOL]    — fetch market data (default BTC/USDT)\n"
                "  help               — show this message\n"
                "  exit               — quit"
            )

        return "Unknown command. Type 'help' for options."


if __name__ == "__main__":
    maya = MayaTermux()
    print("Type 'help' for available commands, 'exit' to quit.\n")
    while True:
        try:
            user = input("[ID]: ").strip()
            if not user:
                continue
            order = input(f"[{user}] Order: ").strip()
            if order.lower() == "exit":
                print("Shutting down.")
                break
            print(f"Maya: {maya.handle_boss(user, order)}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nShutting down.")
            break
