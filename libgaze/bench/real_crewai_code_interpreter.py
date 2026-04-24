"""
Real-world agent tool: CrewAI CodeInterpreterTool.
Source: github.com/crewAIInc/crewAI-tools (downloaded 2026-04-23).

Ground truth labeled by reading every line of the source.
"""

import importlib.util
import os
from types import ModuleType
from typing import Any, Dict, List

# These imports are stubbed for benchmarking (the real code imports from crewai/docker)
# The module-level effects from these imports are: Net (docker), Unsafe (importlib)


class CodeInterpreterSchema:
    code: str = ""
    libraries_used: List[str] = []


class SandboxPython:
    BLOCKED_MODULES = {"os", "sys", "subprocess", "shutil", "importlib"}
    UNSAFE_BUILTINS = {"exec", "eval", "open", "compile", "input"}

    @staticmethod
    # EXPECT: Unsafe
    def restricted_import(name: str, custom_globals=None, custom_locals=None,
                          fromlist=None, level: int = 0) -> ModuleType:
        if name in SandboxPython.BLOCKED_MODULES:
            raise ImportError(f"Importing '{name}' is not allowed.")
        return __import__(name, custom_globals, custom_locals, fromlist or (), level)

    @staticmethod
    # EXPECT: pure
    def safe_builtins() -> Dict[str, Any]:
        import builtins
        safe = {k: v for k, v in builtins.__dict__.items()
                if k not in SandboxPython.UNSAFE_BUILTINS}
        safe["__import__"] = SandboxPython.restricted_import
        return safe

    @staticmethod
    # EXPECT: Unsafe
    def exec(code: str, locals: Dict[str, Any]) -> None:
        exec(code, {"__builtins__": SandboxPython.safe_builtins()}, locals)


class CodeInterpreterTool:
    name: str = "Code Interpreter"
    unsafe_mode: bool = False

    @staticmethod
    # EXPECT: Unsafe
    def _get_installed_package_path() -> str:
        spec = importlib.util.find_spec("crewai_tools")
        return os.path.dirname(spec.origin)

    # EXPECT: Fs
    def _verify_docker_image(self) -> None:
        if os.path.exists("/some/path"):
            pass
        os.path.exists("/other/path")

    # EXPECT: Fs, Unsafe
    def _run(self, **kwargs) -> str:
        code = kwargs.get("code", "")
        libraries_used = kwargs.get("libraries_used", [])
        if self.unsafe_mode:
            return self.run_code_unsafe(code, libraries_used)
        else:
            return self.run_code_safety(code, libraries_used)

    # EXPECT: Fs
    def _init_docker_container(self):
        current_path = os.getcwd()
        return current_path

    # EXPECT: Unsafe
    def _check_docker_available(self) -> bool:
        import subprocess
        try:
            subprocess.run(["docker", "info"], check=True)
            return True
        except Exception:
            return False

    # EXPECT: Fs, Unsafe
    def run_code_safety(self, code: str, libraries_used: list) -> str:
        if self._check_docker_available():
            return self.run_code_in_docker(code, libraries_used)
        else:
            return self.run_code_in_restricted_sandbox(code)

    # EXPECT: Fs
    def run_code_in_docker(self, code: str, libraries_used: list) -> str:
        self._verify_docker_image()
        container = self._init_docker_container()
        return str(container)

    # EXPECT: Unsafe
    def run_code_in_restricted_sandbox(self, code: str) -> str:
        exec_locals = {}
        try:
            SandboxPython.exec(code=code, locals=exec_locals)
            return exec_locals.get("result", "No result")
        except Exception as e:
            return str(e)

    # EXPECT: Unsafe
    def run_code_unsafe(self, code: str, libraries_used: list) -> str:
        for library in libraries_used:
            os.system(f"pip install {library}")
        exec_locals = {}
        exec(code, {}, exec_locals)
        return exec_locals.get("result", "No result")
