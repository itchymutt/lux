"""
Tricky cases for effect detection. Each function has a comment saying
what the CORRECT answer is. Used to measure precision and recall.
"""

import os
import json
import subprocess
from pathlib import Path


# CORRECT: can Fs (reads a file)
def read_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


# CORRECT: can Fs (writes a file)
def write_output(path: str, data: dict) -> None:
    Path(path).write_text(json.dumps(data))


# CORRECT: can Env
def get_api_key() -> str:
    return os.environ.get("API_KEY", "")


# CORRECT: can Unsafe (subprocess)
def run_linter(path: str) -> str:
    result = subprocess.run(["ruff", "check", path], capture_output=True, text=True)
    return result.stdout


# CORRECT: (pure) - os.path.join is pure string manipulation
def build_path(base: str, name: str) -> str:
    return os.path.join(base, name)


# CORRECT: can Console (print)
def log_message(msg: str) -> None:
    print(f"[LOG] {msg}")


# CORRECT: (pure) - no effects, just data transformation
def parse_headers(raw: str) -> dict:
    result = {}
    for line in raw.strip().split("\n"):
        if ": " in line:
            key, value = line.split(": ", 1)
            result[key] = value
    return result


# CORRECT: can Fs (os.listdir)
def list_python_files(directory: str) -> list:
    return [f for f in os.listdir(directory) if f.endswith(".py")]


# TRICKY: calls a method on an object that MIGHT be effectful,
# but libgaze can't know. Should be (pure) from static analysis.
def process_items(items: list, handler) -> list:
    return [handler.process(item) for item in items]


# TRICKY: getattr-based dynamic dispatch. libgaze can't trace this.
# CORRECT from static analysis: (pure)
# ACTUAL at runtime: depends on what action_name resolves to
def dispatch(obj, action_name: str):
    method = getattr(obj, action_name)
    return method()


# CORRECT: can Unsafe (eval)
def evaluate_expression(expr: str):
    return eval(expr)


# CORRECT: can Env (os.getenv)
def load_settings() -> dict:
    return {
        "debug": os.getenv("DEBUG", "false") == "true",
        "port": int(os.getenv("PORT", "8080")),
    }
