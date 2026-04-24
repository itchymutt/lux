"""
Network and HTTP patterns.
"""

import json
import socket
from urllib.parse import urlparse, urlencode


# EXPECT: pure
def parse_url(url: str) -> dict:
    """urllib.parse is pure string parsing, not network I/O."""
    parsed = urlparse(url)
    return {
        "scheme": parsed.scheme,
        "host": parsed.netloc,
        "path": parsed.path,
    }


# EXPECT: pure
def build_query_string(params: dict) -> str:
    """urlencode is pure string formatting."""
    return urlencode(params)


# EXPECT: Net
def open_socket(host: str, port: int) -> socket.socket:
    """socket is Net."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s


# EXPECT: pure
def format_headers(headers: dict) -> str:
    """Pure string formatting of HTTP headers."""
    lines = [f"{k}: {v}" for k, v in headers.items()]
    return "\r\n".join(lines)


# EXPECT: pure
def parse_json_response(text: str) -> dict:
    """json.loads is pure."""
    return json.loads(text)
