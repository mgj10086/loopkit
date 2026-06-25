"""
LoopCode Runtime — LLM integration layer.

Calls LLM APIs (Claude, OpenAI, or custom) to execute agent prompts.
Supports streaming, structured output, and token tracking.
"""

from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass
from typing import Literal

import httpx


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: int
    cost_usd: float


class LLMClient:
    """Client for calling LLM APIs with token tracking and budgeting."""

    PRICING = {
        "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},   # $/M tokens
        "claude-opus-4-8":   {"input": 15.0, "output": 75.0},
        "claude-haiku-4-5":  {"input": 0.25, "output": 1.25},
        "gpt-4o":            {"input": 2.5,  "output": 10.0},
        "gpt-4o-mini":       {"input": 0.15, "output": 0.6},
    }

    def __init__(
        self,
        provider: Literal["anthropic", "openai", "custom"] = "anthropic",
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        base_url: str | None = None,
    ):
        self.provider = provider
        self.model = model
        self.base_url = base_url or self._default_base_url()
        self.api_key = api_key or os.environ.get(self._env_var_name(), "")

    def _default_base_url(self) -> str:
        if self.provider == "anthropic":
            return "https://api.anthropic.com/v1"
        elif self.provider == "openai":
            return "https://api.openai.com/v1"
        return ""

    def _env_var_name(self) -> str:
        if self.provider == "anthropic":
            return "ANTHROPIC_API_KEY"
        elif self.provider == "openai":
            return "OPENAI_API_KEY"
        return "LLM_API_KEY"

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        pricing = self.PRICING.get(self.model, {"input": 3.0, "output": 15.0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def complete(self, prompt: str, system: str | None = None) -> LLMResponse:
        """Send a completion request to the LLM."""
        start = time.time()

        if self.provider == "anthropic":
            return self._call_anthropic(prompt, system)
        elif self.provider == "openai":
            return self._call_openai(prompt, system)
        else:
            return self._call_custom(prompt, system)

    def _call_anthropic(self, prompt: str, system: str | None) -> LLMResponse:
        """Call Anthropic's Claude API."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        body = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system

        start = time.time()
        try:
            resp = httpx.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=body,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Anthropic API error: {e}") from e

        duration = int((time.time() - start) * 1000)
        content = data["content"][0]["text"]
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration,
            cost_usd=self._estimate_cost(input_tokens, output_tokens),
        )

    def _call_openai(self, prompt: str, system: str | None) -> LLMResponse:
        headers = {
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self.model,
            "messages": messages,
        }

        start = time.time()
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e

        duration = int((time.time() - start) * 1000)
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration,
            cost_usd=self._estimate_cost(input_tokens, output_tokens),
        )

    def _call_custom(self, prompt: str, system: str | None) -> LLMResponse:
        """Call a custom/compatible endpoint."""
        return self._call_openai(prompt, system)  # OpenAI-compatible
