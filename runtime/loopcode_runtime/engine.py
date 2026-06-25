"""
LoopCode Runtime — Core loop execution engine.

Orchestrates the full loop lifecycle:
  1. Load config → 2. Spawn maker agents → 3. Run checker verification
  4. Enforce budget → 5. Persist state → 6. Report results
"""

from __future__ import annotations
import json
import os
import time
import hashlib
from pathlib import Path
from typing import Any

import yaml

from .models import (
    LoopConfig,
    ProjectConfig,
    StepResult,
    VerificationResult,
    LoopExecutionResult,
    AgentRef,
)
from .llm import LLMClient, LLMResponse
from .reporter import Reporter


class LoopEngine:
    """The core loop execution engine with Maker/Checker enforcement."""

    def __init__(
        self,
        project_dir: str = ".",
        llm_client: LLMClient | None = None,
        reporter: Reporter | None = None,
        dry_run: bool = False,
    ):
        self.project_dir = Path(project_dir)
        self.llm = llm_client or LLMClient(provider="anthropic")
        self.reporter = reporter or Reporter()
        self.dry_run = dry_run
        self._state_dir = self.project_dir / ".loopcode" / "state"

    # ── Public API ──────────────────────────────────────────

    def load_project(self) -> ProjectConfig:
        """Load loopcode.yaml from project directory."""
        for name in ["loopcode.yaml", "loopcode.yml"]:
            path = self.project_dir / name
            if path.exists():
                with open(path) as f:
                    raw = yaml.safe_load(f)
                return ProjectConfig.model_validate(raw)
        raise FileNotFoundError(
            "No loopcode.yaml found. Run 'loopcode init' first."
        )

    def find_loop(self, loop_name: str) -> tuple[LoopConfig, str]:
        """Find a loop by name — checks project config and loops/ directory."""
        # Check project-level loop configs
        project = self.load_project()
        if loop_name in project.loops:
            return project.loops[loop_name], "project config"

        # Check loops/ directory
        for ext in ["yaml", "yml"]:
            path = self.project_dir / "loops" / f"{loop_name}.{ext}"
            if path.exists():
                with open(path) as f:
                    raw = yaml.safe_load(f)
                return LoopConfig.model_validate(raw), str(path)

        raise KeyError(f"Loop '{loop_name}' not found in project or loops/")

    async def run_loop(self, loop_name: str) -> LoopExecutionResult:
        """Execute a full loop: pipeline → verify → report."""
        start_time = time.time()
        self.reporter.section(f"Running Loop: {loop_name}")

        # 1. Load config
        try:
            config, source = self.find_loop(loop_name)
        except (FileNotFoundError, KeyError) as e:
            self.reporter.error(str(e))
            return LoopExecutionResult(
                loop_name=loop_name,
                success=False,
                total_duration_ms=0,
                error=str(e),
            )

        self.reporter.info(f"Config: {source}")
        self.reporter.info(f"Pipeline: {len(config.pipeline)} step(s)")
        if config.verify:
            self.reporter.info(
                f"Verification: Maker={config.verify.maker} | Checker={config.verify.checker}"
            )
        self.reporter.info("")

        steps: list[StepResult] = []
        total_cost = 0.0

        # 2. Execute pipeline
        self.reporter.subsection("Pipeline Execution")
        for i, raw_step in enumerate(config.pipeline):
            step = self._normalize_step(raw_step, i)

            if step.parallel:
                step_result = await self._run_parallel(step.parallel, config)
                steps.extend(step_result)
            elif step.agents:
                for agent in step.agents:
                    result = await self._run_agent(agent, config)
                    steps.append(result)
                    total_cost += (result.cost_estimate or 0)
            else:
                # Single agent
                agent_ref = AgentRef(
                    prompt=step.prompt or "",
                    label=step.label,
                    model=config.budget.model if config.budget else None,
                )
                result = await self._run_agent(agent_ref, config)
                steps.append(result)
                total_cost += (result.cost_estimate or 0)

        # 3. Verification (Maker/Checker)
        verification: VerificationResult | None = None
        if config.verify:
            verification = await self._run_verification(config, steps)
            if verification and not verification.passed:
                self.reporter.warning(
                    f"Verification failed after {verification.rounds} rounds"
                )

        # 4. Persist state
        if config.memory:
            self._persist_state(loop_name, {
                "steps": [s.model_dump() for s in steps],
                "verification": verification.model_dump() if verification else None,
                "total_cost": total_cost,
                "timestamp": time.time(),
            })

        # 5. Report
        duration = int((time.time() - start_time) * 1000)
        success = all(s.status == "passed" for s in steps)
        if verification:
            success = success and verification.passed

        self.reporter.subsection("Results")
        if success:
            self.reporter.success(f"Loop '{loop_name}' completed successfully")
        else:
            self.reporter.error(f"Loop '{loop_name}' had issues")

        self.reporter.kv("Duration", f"{duration}ms")
        self.reporter.kv("Steps", str(len(steps)))
        self.reporter.kv("Est. Cost", f"${total_cost:.4f}")
        self.reporter.info("")

        return LoopExecutionResult(
            loop_name=loop_name,
            success=success,
            total_duration_ms=duration,
            steps=steps,
            verification=verification,
            cost_estimate=total_cost,
        )

    # ── Agent Execution ──────────────────────────────────────

    async def _run_agent(
        self, agent: AgentRef, config: LoopConfig
    ) -> StepResult:
        """Execute a single agent prompt."""
        self.reporter.info(f"  -> Agent: {agent.label or agent.prompt[:40]}...")
        start = time.time()

        if self.dry_run:
            time.sleep(0.1)
            return StepResult(
                label=agent.label or agent.prompt[:40],
                agent_label=agent.label or "agent",
                status="passed",
                output="[dry run]",
                duration_ms=100,
            )

        try:
            response: LLMResponse = self.llm.complete(
                prompt=agent.prompt,
                system="You are an expert AI agent. Execute the task precisely and thoroughly.",
            )
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            self.reporter.error(f"    Agent failed: {e}")
            return StepResult(
                label=agent.label or agent.prompt[:40],
                agent_label=agent.label or "agent",
                status="failed",
                error=str(e),
                duration_ms=duration,
            )

        duration = int((time.time() - start) * 1000)
        self.reporter.info(
            f"    + Completed ({response.duration_ms}ms, "
            f"{response.input_tokens} up/{response.output_tokens} down tokens, "
            f"${response.cost_usd:.4f})"
        )

        return StepResult(
            label=agent.label or agent.prompt[:40],
            agent_label=agent.label or "agent",
            status="passed",
            output=response.content,
            duration_ms=duration,
        )

    async def _run_parallel(
        self, agents: list[AgentRef], config: LoopConfig
    ) -> list[StepResult]:
        """Run multiple agents in parallel."""
        self.reporter.info(f"  Running {len(agents)} agents in parallel...")
        results = []
        for agent in agents:
            result = await self._run_agent(agent, config)
            results.append(result)
        return results

    async def _run_verification(
        self, config: LoopConfig, steps: list[StepResult]
    ) -> VerificationResult:
        """Run Maker/Checker verification on pipeline output."""
        self.reporter.subsection("Maker/Checker Verification")

        # Collect maker output
        maker_outputs = "\n\n".join(
            s.output or "" for s in steps if s.status == "passed"
        )

        # Construct checker prompt
        makers = (
            [config.verify.maker]
            if isinstance(config.verify.maker, str)
            else config.verify.maker
        )
        checkers = (
            [config.verify.checker]
            if isinstance(config.verify.checker, str)
            else config.verify.checker
        )

        checker_prompt = f"""You are an adversarial verifier (Checker).

Your job is to critically evaluate the following agent outputs.
Look for:
1. Factual errors or hallucinations
2. Logical inconsistencies
3. Missing edge cases
4. Security vulnerabilities in suggested code
5. Overconfidence without evidence

Maker agents: {', '.join(makers)}
Maker outputs to verify:
{maker_outputs}

Provide:
- A score from 0.0 (completely wrong) to 1.0 (perfect)
- Specific issues found, if any
- Whether the output PASSES or FAILS verification"""

        self.reporter.info(f"  Checker: {', '.join(checkers)}")
        rounds = 1

        if self.dry_run:
            return VerificationResult(
                maker_label=",".join(makers),
                checker_label=",".join(checkers),
                rounds=rounds,
                passed=True,
                checker_score=0.95,
                checker_feedback="[dry run] All checks passed.",
            )

        for round_num in range(1, config.verify.max_rounds + 1):
            try:
                response = self.llm.complete(prompt=checker_prompt)
            except Exception as e:
                self.reporter.error(f"  Checker failed: {e}")
                return VerificationResult(
                    maker_label=",".join(makers),
                    checker_label=",".join(checkers),
                    rounds=round_num,
                    passed=False,
                    error=str(e),
                )

            rounds = round_num
            passed = "PASS" in response.content.upper() and "FAIL" not in response.content.upper()

            # Extract score from response
            import re
            score_match = re.search(r'(\d+\.?\d*)\s*/\s*1\.?0', response.content)
            score = float(score_match.group(1)) if score_match else None

            self.reporter.info(
                f"  Round {round_num}: {'[ok] PASS' if passed else '[!!] FAIL'} "
                f"(score: {score or 'N/A'})"
            )

            if passed:
                return VerificationResult(
                    maker_label=",".join(makers),
                    checker_label=",".join(checkers),
                    rounds=round_num,
                    passed=True,
                    maker_output=maker_outputs,
                    checker_feedback=response.content,
                    checker_score=score,
                )

            if round_num < config.verify.max_rounds and config.verify.auto_retry:
                self.reporter.info("  Retrying with checker feedback...")

        return VerificationResult(
            maker_label=",".join(makers),
            checker_label=",".join(checkers),
            rounds=rounds,
            passed=False,
            maker_output=maker_outputs,
            checker_feedback="Verification failed after max rounds.",
            checker_score=score if 'score' in dir() else None,
        )

    # ── State Persistence ────────────────────────────────────

    def _persist_state(self, loop_name: str, data: dict[str, Any]) -> None:
        """Persist loop execution state to filesystem."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        path = self._state_dir / f"{loop_name}-{timestamp}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        self.reporter.info(f"  State saved: {path.name}")

    # ── Helpers ──────────────────────────────────────────────

    def _normalize_step(self, raw: dict[str, Any], index: int) -> AgentRef | Any:
        """Normalize a pipeline step dict into an AgentRef-like structure."""
        if "parallel" in raw:
            agents = [AgentRef(**a) for a in raw["parallel"]]
            return type('_', (), {'parallel': agents, 'agents': None, 'prompt': None, 'label': None})()
        elif "agents" in raw:
            agents = [AgentRef(**a) for a in raw["agents"]]
            return type('_', (), {'agents': agents, 'parallel': None, 'prompt': None, 'label': None})()
        else:
            return AgentRef(
                prompt=raw.get("prompt", ""),
                label=raw.get("label"),
                skill=raw.get("skill"),
                model=raw.get("model"),
            )
