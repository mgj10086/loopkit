"""
LoopKit Runtime — CLI entry point (click).
"""

from __future__ import annotations
import asyncio
import sys
from pathlib import Path

import click

from .engine import LoopEngine
from .llm import LLMClient
from .reporter import Reporter


@click.group()
@click.option("--project-dir", "-d", default=".", help="Project directory")
@click.option("--dry-run", is_flag=True, help="Simulate without LLM calls")
@click.option("--model", default="claude-sonnet-4-6", help="LLM model")
@click.option("--provider", default="anthropic",
              type=click.Choice(["anthropic", "openai", "custom"]))
@click.pass_context
def cli(ctx, project_dir, dry_run, model, provider):
    """LoopKit Runtime — Run autonomous AI agent loops."""
    ctx.ensure_object(dict)
    reporter = Reporter()
    llm = LLMClient(provider=provider, model=model)
    engine = LoopEngine(
        project_dir=project_dir,
        llm_client=llm,
        reporter=reporter,
        dry_run=dry_run,
    )
    ctx.obj["engine"] = engine
    ctx.obj["reporter"] = reporter


@cli.command()
@click.pass_context
def validate(ctx):
    """Validate loop configuration and show LRS scores."""
    engine: LoopEngine = ctx.obj["engine"]
    reporter: Reporter = ctx.obj["reporter"]

    try:
        project = engine.load_project()
    except FileNotFoundError as e:
        reporter.error(str(e))
        sys.exit(1)

    reporter.section("LoopKit Validation")

    # List project-level loops
    for name, config in project.loops.items():
        reporter.info(f"  📋 {name}: {config.description or '(no description)'}")

    # Check loop files
    loops_dir = Path(engine.project_dir) / "loops"
    if loops_dir.exists():
        for f in sorted(loops_dir.glob("*.yaml")):
            reporter.info(f"  📄 {f.name}")
    elif not project.loops:
        reporter.warning("No loops defined. Run 'loopkit init' or add loops manually.")

    reporter.success(f"Project {engine.project_dir} is valid")
    reporter.info("")


@cli.command()
@click.argument("loop_name")
@click.pass_context
def run(ctx, loop_name):
    """Execute a named loop."""
    engine: LoopEngine = ctx.obj["engine"]
    reporter: Reporter = ctx.obj["reporter"]

    result = asyncio.run(engine.run_loop(loop_name))

    if result.success:
        reporter.success(f"Loop '{loop_name}' completed successfully")
    else:
        reporter.error(f"Loop '{loop_name}' failed: {result.error}")
        sys.exit(1)


@cli.command()
@click.pass_context
def demo(ctx):
    """Run a demo of all built-in loops."""
    engine: LoopEngine = ctx.obj["engine"]
    reporter: Reporter = ctx.obj["reporter"]

    reporter.section("LoopKit Demo - Built-in Loops")

    loops = [
        ("pr-review", "Multi-agent code review with Maker/Checker"),
        ("daily-triage", "Automated issue categorization"),
    ]

    for name, desc in loops:
        reporter.subsection(f"Demo: {name}")
        reporter.info(f"  Description: {desc}")
        reporter.info(f"  Mode: {'dry run' if engine.dry_run else 'live'}")

        result = asyncio.run(engine.run_loop(name))

        if result.success:
            reporter.success(f"{name} passed")
        else:
            reporter.error(f"{name} failed: {result.error}")

        reporter.info("")

    reporter.section("Demo Complete")


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
