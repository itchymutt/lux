"""
Class method patterns. Tests intra-module call graph propagation.
"""

import os
import subprocess


class FileManager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    # EXPECT: Fs
    def read(self, name: str) -> str:
        path = os.path.join(self.base_dir, name)
        with open(path) as f:
            return f.read()

    # EXPECT: Fs
    def write(self, name: str, content: str) -> None:
        path = os.path.join(self.base_dir, name)
        with open(path, "w") as f:
            f.write(content)

    # EXPECT: Fs
    def exists(self, name: str) -> bool:
        path = os.path.join(self.base_dir, name)
        return os.path.exists(path)

    # EXPECT: Fs
    def read_if_exists(self, name: str) -> str | None:
        if self.exists(name):
            return self.read(name)
        return None

    # EXPECT: Fs
    def copy(self, src: str, dst: str) -> None:
        content = self.read(src)
        self.write(dst, content)


class CommandRunner:
    # EXPECT: Unsafe
    def run(self, cmd: list) -> str:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout

    # EXPECT: Unsafe
    def run_checked(self, cmd: list) -> str:
        result = self.run(cmd)
        if not result:
            raise RuntimeError("Command produced no output")
        return result

    # EXPECT: pure
    def format_command(self, cmd: list) -> str:
        return " ".join(cmd)


class MixedService:
    # EXPECT: Env
    def get_config(self) -> dict:
        return {
            "host": os.getenv("HOST", "localhost"),
            "port": int(os.getenv("PORT", "8080")),
        }

    # EXPECT: Console
    def log(self, msg: str) -> None:
        print(f"[MixedService] {msg}")

    # EXPECT: Console, Env
    def start(self) -> None:
        config = self.get_config()
        self.log(f"Starting on {config['host']}:{config['port']}")


class PureCalculator:
    def __init__(self, precision: int = 2):
        self.precision = precision

    # EXPECT: pure
    def add(self, a: float, b: float) -> float:
        return round(a + b, self.precision)

    # EXPECT: pure
    def multiply(self, a: float, b: float) -> float:
        return round(a * b, self.precision)

    # EXPECT: pure
    def compound(self, a: float, b: float, c: float) -> float:
        return self.add(self.multiply(a, b), c)
