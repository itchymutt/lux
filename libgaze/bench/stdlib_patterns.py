"""
Standard library patterns. Tests detection of common Python idioms.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


# EXPECT: Fs
def read_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


# EXPECT: Fs
def write_json(path: str, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f)


# EXPECT: Fs
def pathlib_read(path: str) -> str:
    return Path(path).read_text()


# EXPECT: Fs
def pathlib_write(path: str, content: str) -> None:
    Path(path).write_text(content)


# EXPECT: Fs
def list_directory(path: str) -> list:
    return os.listdir(path)


# EXPECT: Fs
def walk_tree(root: str) -> list:
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        results.extend(filenames)
    return results


# EXPECT: Fs
def check_exists(path: str) -> bool:
    return os.path.exists(path)


# EXPECT: pure
def join_paths(base: str, name: str) -> str:
    return os.path.join(base, name)


# EXPECT: pure
def get_extension(path: str) -> str:
    return os.path.splitext(path)[1]


# EXPECT: pure
def get_dirname(path: str) -> str:
    return os.path.dirname(path)


# EXPECT: pure
def get_basename(path: str) -> str:
    return os.path.basename(path)


# EXPECT: Env
def read_env(key: str) -> str:
    return os.getenv(key, "")


# EXPECT: Env
def read_environ(key: str) -> str:
    return os.environ.get(key, "")


# EXPECT: Env
def get_pid() -> int:
    return os.getpid()


# EXPECT: Unsafe
def shell_exec(cmd: str) -> int:
    return os.system(cmd)


# EXPECT: Unsafe
def run_subprocess(cmd: list) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


# EXPECT: Unsafe
def eval_expr(expr: str):
    return eval(expr)


# EXPECT: Unsafe
def exec_code(code: str):
    exec(code)


# EXPECT: Console
def print_message(msg: str) -> None:
    print(msg)


# EXPECT: Console
def read_input(prompt: str) -> str:
    return input(prompt)


# EXPECT: Fail
def exit_program(code: int) -> None:
    sys.exit(code)


# EXPECT: Fs
def make_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


# EXPECT: Fs
def remove_file(path: str) -> None:
    os.remove(path)


# EXPECT: pure
def parse_json(text: str) -> dict:
    return json.loads(text)


# EXPECT: pure
def format_json(data: dict) -> str:
    return json.dumps(data, indent=2)
