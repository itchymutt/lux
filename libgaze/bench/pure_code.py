"""
Pure functions only. Every function here should be detected as pure.
Tests for false positives.
"""

import json
import math
import re
from dataclasses import dataclass
from enum import Enum


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


@dataclass
class Point:
    x: float
    y: float


@dataclass
class Rect:
    origin: Point
    width: float
    height: float


# EXPECT: pure
def distance(a: Point, b: Point) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


# EXPECT: pure
def midpoint(a: Point, b: Point) -> Point:
    return Point(x=(a.x + b.x) / 2, y=(a.y + b.y) / 2)


# EXPECT: pure
def rect_area(r: Rect) -> float:
    return r.width * r.height


# EXPECT: pure
def rect_contains(r: Rect, p: Point) -> bool:
    return (r.origin.x <= p.x <= r.origin.x + r.width and
            r.origin.y <= p.y <= r.origin.y + r.height)


# EXPECT: pure
def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# EXPECT: pure
def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


# EXPECT: pure
def parse_csv_line(line: str) -> list:
    return [field.strip() for field in line.split(",")]


# EXPECT: pure
def flatten(nested: list) -> list:
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


# EXPECT: pure
def group_by(items: list, key: str) -> dict:
    groups = {}
    for item in items:
        k = item.get(key, "unknown")
        groups.setdefault(k, []).append(item)
    return groups


# EXPECT: pure
def deep_merge(a: dict, b: dict) -> dict:
    result = dict(a)
    for key, value in b.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# EXPECT: pure
def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


# EXPECT: pure
def truncate(text: str, max_len: int = 100, suffix: str = "...") -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - len(suffix)] + suffix


# EXPECT: pure
def color_to_hex(color: Color) -> str:
    mapping = {Color.RED: "#ff0000", Color.GREEN: "#00ff00", Color.BLUE: "#0000ff"}
    return mapping.get(color, "#000000")


# EXPECT: pure
def json_roundtrip(data: dict) -> dict:
    """json.dumps and json.loads are pure (string in, string out)."""
    return json.loads(json.dumps(data))


# EXPECT: pure
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
