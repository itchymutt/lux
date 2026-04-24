"""
Edge cases and tricky patterns. Tests the boundaries of static analysis.
"""

import os
import time
import random
from datetime import datetime
from pathlib import Path


# EXPECT: pure
def string_operations(text: str) -> str:
    """Pure string manipulation, no effects."""
    return text.strip().lower().replace("-", "_")


# EXPECT: pure
def list_comprehension(items: list) -> list:
    """Pure data transformation."""
    return [x * 2 for x in items if x > 0]


# EXPECT: pure
def dict_merge(a: dict, b: dict) -> dict:
    """Pure dict operation."""
    return {**a, **b}


# EXPECT: pure
def nested_pure(x: int) -> int:
    """Calls only pure operations."""
    return abs(x) + max(0, x) + min(100, x)


# EXPECT: Time
def get_timestamp() -> str:
    """Reads the clock."""
    return datetime.now().isoformat()


# EXPECT: Time
def sleep_briefly() -> None:
    """Sleeps."""
    time.sleep(0.1)


# EXPECT: Rand
def generate_id() -> str:
    """Generates random data."""
    return str(random.randint(1000, 9999))


# EXPECT: Rand
def shuffle_list(items: list) -> list:
    """Mutates via randomness."""
    result = list(items)
    random.shuffle(result)
    return result


# EXPECT: Fs
def context_manager_read(path: str) -> str:
    """open() inside a with statement."""
    with open(path) as f:
        return f.read()


# EXPECT: Fs, Console
def read_and_print(path: str) -> None:
    """Two effects in one function."""
    with open(path) as f:
        content = f.read()
    print(content)


# EXPECT: Env, Console
def debug_env(key: str) -> None:
    """Two effects: reads env, prints to console."""
    value = os.getenv(key, "(not set)")
    print(f"{key}={value}")


# EXPECT: pure
def dynamic_dispatch(obj, method_name: str):
    """getattr-based dispatch. Static analysis can't trace this.
    Correct answer from static analysis is pure."""
    method = getattr(obj, method_name)
    return method()


# EXPECT: pure
def callback_pattern(items: list, fn) -> list:
    """Higher-order function. Can't know what fn does.
    Correct answer from static analysis is pure."""
    return [fn(item) for item in items]


# EXPECT: pure
def exception_handling() -> str:
    """try/except with no effectful calls."""
    try:
        return str(1 / 1)
    except ZeroDivisionError:
        return "error"


# EXPECT: Fs
def conditional_effect(should_write: bool, path: str) -> None:
    """Effect is conditional but still present in the code."""
    if should_write:
        with open(path, "w") as f:
            f.write("data")


# EXPECT: Console
def f_string_with_print(name: str) -> None:
    """print with f-string."""
    print(f"Hello, {name}!")


# EXPECT: pure
def walrus_operator(items: list) -> list:
    """Walrus operator, no effects."""
    return [y for x in items if (y := x * 2) > 10]


# EXPECT: Fs
def pathlib_operations(base: str) -> list:
    """pathlib glob touches the filesystem."""
    return list(Path(base).glob("*.py"))


# EXPECT: pure
def type_annotations_only(x: "os.PathLike") -> str:
    """Type annotation mentions os but no actual os calls."""
    return str(x)


# EXPECT: Fs, Unsafe
def pickle_load(path: str):
    """pickle is Unsafe (arbitrary code execution on deserialization).
    open() is Fs."""
    import pickle
    with open(path, "rb") as f:
        return pickle.load(f)


# EXPECT: Unsafe
def dynamic_import(module_name: str):
    """importlib.import_module is Unsafe."""
    import importlib
    return importlib.import_module(module_name)
