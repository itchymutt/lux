"""
Async and concurrency patterns.
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor


# EXPECT: Async
async def fetch_url(url: str) -> str:
    """async def implies Async."""
    await asyncio.sleep(1)
    return f"response from {url}"


# EXPECT: Async
async def gather_results(urls: list) -> list:
    """asyncio.gather is Async."""
    tasks = [fetch_url(url) for url in urls]
    return await asyncio.gather(*tasks)


# EXPECT: Async
def spawn_thread(target) -> threading.Thread:
    """threading is Async."""
    t = threading.Thread(target=target)
    t.start()
    return t


# EXPECT: Async
def thread_pool(fn, items: list) -> list:
    """ThreadPoolExecutor is Async."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(fn, items))


# EXPECT: pure
def prepare_tasks(items: list) -> list:
    """Pure data preparation, no async."""
    return [(item, item * 2) for item in items]
