"""
Real-world agent tool: CrewAI SeleniumScrapingTool (simplified).
Source: github.com/crewAIInc/crewAI-tools (downloaded 2026-04-23).

Simplified to remove external dependencies while preserving the effect patterns.
Ground truth labeled by reading every line of the source.
"""

import re
import time
import subprocess
from urllib.parse import urlparse


class SeleniumScrapingTool:
    name: str = "Read a website content"
    driver = None
    wait_time: int = 3

    # EXPECT: pure
    def validate_url(self, url: str) -> bool:
        if not url:
            return False
        if not re.match(r"^https?://", url):
            return False
        result = urlparse(url)
        return all([result.scheme, result.netloc])

    # EXPECT: Unsafe
    def install_dependencies(self) -> None:
        subprocess.run(
            ["uv", "pip", "install", "selenium", "webdriver-manager"],
            check=True,
        )

    # EXPECT: Time
    def _make_request(self, url: str, cookie: dict | None, wait_time: int) -> None:
        if not url:
            raise ValueError("URL cannot be empty")
        # self.driver.get(url) would be Net but we can't trace injected objects
        time.sleep(wait_time)
        if cookie:
            time.sleep(wait_time)
            time.sleep(wait_time)

    # EXPECT: pure
    def _get_content(self, css_element: str | None) -> list:
        content = []
        if css_element is None or css_element.strip() == "":
            content.append("body content")
        return content

    # EXPECT: Time
    def _run(self, **kwargs) -> str:
        url = kwargs.get("website_url", "")
        css_element = kwargs.get("css_element", None)
        self._make_request(url, None, self.wait_time)
        content = self._get_content(css_element)
        return "\n".join(content)

    # EXPECT: pure
    def close(self) -> None:
        # self.driver.close() would be Net but can't trace injected objects
        pass
