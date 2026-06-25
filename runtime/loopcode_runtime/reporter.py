"""
LoopCode Runtime — Rich console reporter with structured output.
"""

from __future__ import annotations
import sys
import os


# Set stdout encoding to UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore


EMOJI = {
    "rocket": "[>]",
    "check": "[ok]",
    "warn": "[!]",
    "error": "[!!]",
    "info": "[i]",
    "section": "[=]",
}


class Reporter:
    """Console reporter with structured sections and colored output."""

    def __init__(self, use_color: bool = True):
        self.use_color = use_color and sys.stdout.isatty()

    def _color(self, text: str, color_code: str) -> str:
        if self.use_color:
            return f"\033[{color_code}m{text}\033[0m"
        return text

    def section(self, title: str) -> None:
        """Print a section header."""
        width = 60
        line = f"\n{'=' * width}"
        print(line)
        print(f"  {title}")
        print(f"{'=' * width}")

    def subsection(self, title: str) -> None:
        """Print a subsection header."""
        print(f"\n── {title} {'─' * max(0, 50 - len(title))}")

    def _safe(self, text: str) -> str:
        """Replace unicode chars that might break on Windows."""
        if sys.platform == "win32":
            text = text.replace("\U0001f504", EMOJI["rocket"])
            text = text.replace("✅", EMOJI["check"])
            text = text.replace("⚠️", EMOJI["warn"])
            text = text.replace("❌", EMOJI["error"])
            text = text.replace("ℹ️", EMOJI["info"])
            text = text.replace("\U0001f7e2", EMOJI["check"])
            text = text.replace("\U0001f534", EMOJI["error"])
            text = text.replace("\U0001f4cb", EMOJI["section"])
            text = text.replace("│", "|")
            text = text.replace("─", "-")
            text = text.replace("├", "+")
            text = text.replace("└", "+")
            text = text.replace("┬", "+")
        return text

    def info(self, msg: str) -> None:
        """Print an info message."""
        print(self._color(self._safe(msg), ""))

    def success(self, msg: str) -> None:
        """Print a success message."""
        print(self._color(self._safe(f"[ok] {msg}"), "32"))

    def warning(self, msg: str) -> None:
        """Print a warning message."""
        print(self._color(self._safe(f"[!] {msg}"), "33"))

    def error(self, msg: str) -> None:
        """Print an error message."""
        print(self._color(self._safe(f"[!!] {msg}"), "31"))

    def kv(self, key: str, value: str) -> None:
        """Print a key-value pair."""
        print(f"  {key}: {self._color(value, '36')}")

    def divider(self) -> None:
        """Print a divider line."""
        print(f"  {'─' * 55}")

    def json(self, data: dict) -> None:
        """Print pretty-printed JSON."""
        import json
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
