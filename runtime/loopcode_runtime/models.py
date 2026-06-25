"""
LoopCode Runtime — Pydantic models for loop configuration and execution state.
"""

from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class TriggerConfig(BaseModel):
    type: Literal["webhook", "cron", "manual", "event"]
    event: str | None = None
    cron: str | None = None
    description: str | None = None


class AgentRef(BaseModel):
    prompt: str
    skill: str | None = None
    model: str | None = None
    label: str | None = None


class VerifyConfig(BaseModel):
    maker: str | list[str]
    checker: str | list[str]
    max_rounds: int = Field(default=3, ge=1, le=10)
    auto_retry: bool = True


class BudgetConfig(BaseModel):
    max_tokens: int | None = None
    max_duration_minutes: int | None = None
    max_iterations: int | None = None
    max_cost_usd: float | None = None


class MemoryConfig(BaseModel):
    store: Literal["filesystem", "memory", "claude"] = "filesystem"
    path: str = ".loopcode/state"
    persistence: Literal["full", "summary", "minimal"] = "full"


class PipelineStep(BaseModel):
    prompt: str | None = None
    label: str | None = None
    parallel: list[AgentRef] | None = None
    agents: list[AgentRef] | None = None


class LoopConfig(BaseModel):
    name: str
    description: str | None = None
    trigger: TriggerConfig
    pipeline: list[dict[str, Any]]
    verify: VerifyConfig | None = None
    budget: BudgetConfig | None = None
    memory: MemoryConfig | None = None
    tags: list[str] | None = None


class ProjectConfig(BaseModel):
    version: Literal["1"] = "1"
    settings: dict[str, Any] | None = None
    loops: dict[str, LoopConfig] = {}


# ── Execution State ──────────────────────────────────────────

class StepResult(BaseModel):
    label: str
    agent_label: str
    status: Literal["pending", "running", "passed", "failed"]
    output: str | None = None
    error: str | None = None
    duration_ms: int = 0


class VerificationResult(BaseModel):
    maker_label: str
    checker_label: str
    rounds: int
    passed: bool
    maker_output: str | None = None
    checker_feedback: str | None = None
    checker_score: float | None = None  # 0.0 - 1.0


class LoopExecutionResult(BaseModel):
    loop_name: str
    success: bool
    total_duration_ms: int
    steps: list[StepResult] = []
    verification: VerificationResult | None = None
    error: str | None = None
    lrs_score: int | None = None
    cost_estimate: float | None = None  # USD
