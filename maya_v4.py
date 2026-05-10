import os
import subprocess
import shlex
import re
import sqlite3
import json
import ast
import operator
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)

DB_PATH = "maya_memory.db"


# --- MODULE 1: SAFE CALCULATOR ---
class SafeCalculator:
    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    @classmethod
    def evaluate(cls, expression):
        try:
            node = ast.parse(expression, mode="eval").body
            return cls._eval(node)
        except Exception:
            return None

    @classmethod
    def _eval(cls, node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return cls._operators[type(node.op)](
                cls._eval(node.left), cls._eval(node.right)
            )
        elif isinstance(node, ast.UnaryOp):
            return cls._operators[type(node.op)](cls._eval(node.operand))
        else:
            raise TypeError(node)


# --- MODULE 2: SQLITE MEMORY ---
class MayaMemory:
    """Persistent storage for targets and scan history."""

    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS targets (
                ip         TEXT PRIMARY KEY,
                first_seen TEXT,
                last_seen  TEXT,
                notes      TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS scans (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ip        TEXT,
                timestamp TEXT,
                command   TEXT,
                output    TEXT,
                FOREIGN KEY(ip) REFERENCES targets(ip)
            );
        """)
        self.conn.commit()

    def remember_target(self, ip):
        now = datetime.utcnow().isoformat()
        exists = self.conn.execute(
            "SELECT 1 FROM targets WHERE ip=?", (ip,)
        ).fetchone()
        if exists:
            self.conn.execute(
                "UPDATE targets SET last_seen=? WHERE ip=?", (now, ip)
            )
        else:
            self.conn.execute(
                "INSERT INTO targets (ip, first_seen, last_seen) VALUES (?,?,?)",
                (ip, now, now),
            )
        self.conn.commit()

    def log_scan(self, ip, command, output):
        self.conn.execute(
            "INSERT INTO scans (ip, timestamp, command, output) VALUES (?,?,?,?)",
            (ip, datetime.utcnow().isoformat(), command, output[:2000]),
        )
        self.conn.commit()

    def recall_target(self, ip):
        row = self.conn.execute(
            "SELECT first_seen, last_seen FROM targets WHERE ip=?", (ip,)
        ).fetchone()
        if not row:
            return None
        recent = self.conn.execute(
            "SELECT timestamp, command FROM scans WHERE ip=? ORDER BY id DESC LIMIT 5",
            (ip,),
        ).fetchall()
        return {"first_seen": row[0], "last_seen": row[1], "recent_scans": recent}

    def close(self):
        self.conn.close()


# --- MODULE 3: REACT AGENT WITH APPROVAL GATES ---
class MayaCyberAgent:
    """
    ReAct loop: model produces Thought + Action, user approves before execution.
    shell=False throughout — AI-generated commands cannot invoke shell features.
    """

    def __init__(self, model, memory):
        self.model = model
        self.memory = memory

    def plan_next_step(self, goal, target_ip, observations):
        history_str = "\n".join(
            f"  [Step {o['step']}] CMD: {o['command']}\n"
            f"           OUT: {o['output'][:300]}"
            for o in observations
        )
        prompt = f"""You are Maya, a CTF assistant helping analyze a target machine in an authorized lab.

Target IP : {target_ip}
Goal      : {goal}

Observation history:
{history_str if history_str else "  None yet — this is the first step."}

Respond with ONLY valid JSON (no markdown, no code fences):
{{
  "thought": "what you observe and why you chose this next action",
  "action": "single shell command to run next, OR the string MISSION_DONE if finished"
}}"""
        response = self.model.generate_content(prompt)
        raw = response.text.strip().strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            action_m = re.search(r'"action"\s*:\s*"([^"]+)"', raw)
            thought_m = re.search(r'"thought"\s*:\s*"([^"]+)"', raw)
            return {
                "thought": thought_m.group(1) if thought_m else "Could not parse thought.",
                "action": action_m.group(1) if action_m else "MISSION_DONE",
            }

    def execute_with_approval(self, step, plan):
        """
        Display Thought + Action and require explicit 'y' before running.
        Returns (output_str, is_done).
        """
        sep = "=" * 60
        print(f"\n{sep}")
        print(f"[STEP {step}] THOUGHT : {plan['thought']}")
        print(f"[STEP {step}] ACTION  : {plan['action']}")
        print(sep)

        if plan["action"].strip().upper() == "MISSION_DONE":
            print("[DONE] Maya says the mission is complete.")
            return None, True

        confirm = input("Run this command? [y/n]: ").strip().lower()
        if confirm != "y":
            print("[SKIPPED] Command skipped by user.")
            return "[SKIPPED BY USER]", False

        try:
            args = shlex.split(plan["action"])
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(timeout=60)
            output = stdout if stdout else stderr
        except FileNotFoundError:
            output = f"Command not found: {plan['action'].split()[0]}"
        except subprocess.TimeoutExpired:
            process.kill()
            output = "Command timed out after 60 seconds."
        except Exception as e:
            output = f"Execution error: {e}"

        print(f"\n[OUTPUT]\n{output[:600]}")
        return output, False


# --- MODULE 4: BRAIN & ROUTING ---
class MayaBrain:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.memory = MayaMemory()
        self.agent = MayaCyberAgent(self.model, self.memory)

    def process_request(self, user_text):
        text = user_text.lower()

        # Math
        if any(op in text for op in ["+", "-", "*", "/"]):
            math_expr = "".join(c for c in text if c in "0123456789+-*/(). ")
            result = SafeCalculator.evaluate(math_expr.strip())
            if result is not None:
                return f"The result is {result}, Boss."

        # Recon mission
        if "mission" in text or "scan" in text:
            ip_match = re.search(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", text)
            if ip_match:
                return self.run_recon_loop(ip_match.group(), text)
            return "Boss, please provide a target IP to start the mission."

        # General
        response = self.model.generate_content(
            f"User: {user_text}\nRespond as Maya, a helpful CTF lab assistant."
        )
        return response.text

    def run_recon_loop(self, target_ip, goal):
        # Recall prior history for this target
        history = self.memory.recall_target(target_ip)
        if history:
            print(f"\n[MEMORY] I've seen {target_ip} before.")
            print(f"         First scanned : {history['first_seen'][:19]}")
            print(f"         Last scanned  : {history['last_seen'][:19]}")
            if history["recent_scans"]:
                print("         Recent commands:")
                for ts, cmd in history["recent_scans"]:
                    print(f"           {ts[:19]}  {cmd}")
            if input("\nContinue scanning this target? [y/n]: ").strip().lower() != "y":
                return "Mission aborted by user."

        self.memory.remember_target(target_ip)

        observations = []
        for step in range(1, 6):  # max 5 steps
            plan = self.agent.plan_next_step(goal, target_ip, observations)
            output, done = self.agent.execute_with_approval(step, plan)

            if done:
                break

            self.memory.log_scan(target_ip, plan["action"], output or "")
            observations.append(
                {"step": step, "command": plan["action"], "output": output or ""}
            )

        summary = "\n".join(
            f"  Step {o['step']}: {o['command']}" for o in observations
        )
        return f"\nMission complete for {target_ip}.\nCommands run:\n{summary or '  None.'}"

    def close(self):
        self.memory.close()


# --- MAIN ---
if __name__ == "__main__":
    maya = MayaBrain()
    print("Maya v4 Online.")
    print("SQLite memory active | Human-approval gates enabled")
    print("Note: pipe/redirect syntax is not supported (shell=False for safety).\n")

    try:
        while True:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            ans = maya.process_request(user_input)
            print(f"\nMaya: {ans}\n")
    finally:
        maya.close()
