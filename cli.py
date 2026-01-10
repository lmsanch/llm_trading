#!/usr/bin/env python
"""CLI entry point for LLM trading system."""

import asyncio
import os
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from backend.pipeline import Pipeline, PipelineContext
from backend.pipeline.weekly_pipeline import (
    WeeklyTradingPipeline,
    run_weekly_pipeline,
    run_research_only,
    run_pm_pitches_only,
)
from backend.pipeline.context import USER_QUERY
from backend.pipeline.stages.checkpoint import run_checkpoint, run_all_checkpoints

load_dotenv()


@click.group()
def cli():
    """LLM Trading - Pipeline-first trading system using council decisions."""
    pass


@cli.command()
@click.argument("query", default="")
def council(query: str):
    """Run 3-stage council pipeline on a query (original llm-council pattern)."""
    click.echo(
        "Council command not yet implemented - requires original llm-council stages"
    )
    click.echo("Use 'run_weekly' for the trading pipeline instead")


@cli.command()
@click.option("--query", type=str, default="", help="Optional query for research stage")
@click.option(
    "--mode",
    type=click.Choice(["chat_only", "ranking", "full"]),
    default="full",
    help="Execution mode",
)
@click.option(
    "--search-provider",
    type=click.Choice(["tavily", "brave"]),
    default=None,
    help="Search provider (default: from config)",
)
def run_weekly(query: str = "", mode: str = "full", search_provider: str | None = None):
    """Run full weekly pipeline (research -> PM pitches -> peer review -> chairman -> execute)."""

    async def run():
        click.echo(f"Running full weekly pipeline (mode: {mode})...")
        click.echo("=" * 60)
        click.echo("This will:")
        click.echo("  1. Collect research from Perplexity Sonar Deep Research")
        click.echo("  2. Generate PM pitches from 5 models")

        if mode == "ranking" or mode == "full":
            click.echo("  3. Run anonymized peer review")

        if mode == "full":
            click.echo("  4. Synthesize final chairman decision")

        click.echo("  5. Save trades as PENDING for GUI approval")
        click.echo("=" * 60)

        # Run weekly pipeline
        pipeline = WeeklyTradingPipeline(
            search_provider=search_provider, execution_mode=mode
        )
        result = await pipeline.run(query)

        if result.get("success"):
            click.echo("\n✅ Weekly pipeline complete!")
            click.echo(f"\nTrades saved as PENDING - approve via GUI")
        else:
            click.echo(f"\n❌ Pipeline failed: {result.get('error', 'Unknown error')}")

    asyncio.run(run())


@cli.command()
@click.option("--time", type=str, help='Checkpoint time (e.g., "09:00")')
def checkpoint(time: Optional[str]):
    """Run conviction checkpoint (STAY/EXIT/FLIP/REDUCE)."""

    async def run():
        if time:
            click.echo(f"Running checkpoint at {time}...")
            click.echo("=" * 60)
            click.echo("This will:")
            click.echo("  1. Snapshot current indicators and P/L")
            click.echo("  2. Evaluate conviction update")
            click.echo("  3. Execute action (STAY/EXIT/FLIP/REDUCE)")
            click.echo("=" * 60)

            # Run checkpoint
            result = await run_checkpoint(time)

            if result.get("success"):
                click.echo("\n✅ Checkpoint complete!")
                actions = result.get("actions", [])
                click.echo(f"\nEvaluated {len(actions)} positions")
                for action in actions:
                    click.echo(
                        f"  - {action['account']}: {action['instrument']} {action['action']}"
                    )
            else:
                click.echo(
                    f"\n❌ Checkpoint failed: {result.get('error', 'Unknown error')}"
                )
        else:
            click.echo(
                "Please specify a checkpoint time with --time (e.g., --time 09:00)"
            )

    asyncio.run(run())


@cli.command()
@click.option(
    "--all", "all_checkpoints", is_flag=True, help="Run all checkpoints for today"
)
def run_checkpoints(all_checkpoints: bool):
    """Run all daily checkpoints (09:00, 12:00, 14:00, 15:50 ET)."""

    async def run():
        if all_checkpoints:
            click.echo("Running all checkpoints for today...")
            click.echo("Schedule: 09:00, 12:00, 14:00, 15:50 ET")
            click.echo("=" * 60)

            # Run all checkpoints
            result = await run_all_checkpoints()

            if result.get("success"):
                click.echo("\n✅ All checkpoints complete!")
                checkpoints = result.get("checkpoints", {})
                for time_str, cp_result in checkpoints.items():
                    click.echo(f"\n🕐 {time_str}: {cp_result.get('message', 'Done')}")
            else:
                click.echo(
                    f"\n❌ Checkpoints failed: {result.get('error', 'Unknown error')}"
                )
        else:
            click.echo("Use --all flag to run all checkpoints")

    asyncio.run(run())


@cli.command()
@click.option("--week", type=str, help="Week ID (YYYY-MM-DD)")
def postmortem(week: Optional[str]):
    """Generate weekly postmortem report."""
    if week:
        click.echo(f"Generating postmortem for week {week}...")
        click.echo("This will:")
        click.echo("  1. Analyze all trades executed")
        click.echo("  2. Calculate P/L and metrics")
        click.echo("  3. Compare council vs individual PM performance")
        click.echo("  4. Identify patterns and learnings")
        click.echo("\nNot implemented yet - Phase 2")
    else:
        click.echo("Please specify a week with --week (e.g., --week 2026-01-01)")


@cli.command()
def status():
    """Show system status and configuration."""
    click.echo("LLM Trading System Status")
    click.echo("=" * 40)
    click.echo(f"Working Directory: {Path.cwd()}")
    click.echo(f"Environment: {os.getenv('ENV', 'development')}")

    if os.getenv("REQUESTY_API_KEY"):
        click.echo("✓ Requesty API key configured")
    else:
        click.echo("✗ Requesty API key missing")

    alpaca_keys = [
        os.getenv(f"ALPACA_{acc}_KEY_ID")
        for acc in ["CHATGPT", "GEMINI", "CLAUDE", "GROQ", "DEEPSEEK", "COUNCIL"]
    ]
    if any(alpaca_keys):
        click.echo("✓ Alpaca API keys configured")
    else:
        click.echo("✗ Alpaca API keys missing")

    if os.getenv("PERPLEXITY_API_KEY"):
        click.echo("✓ Perplexity API key configured")
    else:
        click.echo("  (Required) Perplexity API key not configured")

    click.echo(
        f"Database URL: {os.getenv('DATABASE_URL', 'postgresql://localhost:5432/llm_trading')}"
    )


if __name__ == "__main__":
    cli()
