from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .config import RedditResearchConfig
from .pipeline import run_analysis, run_collection

app = typer.Typer(add_completion=False, help="Reddit research pipeline for eye floaters.")
console = Console()


@app.command()
def collect(
    limit: int = typer.Option(25, min=1, help="Posts per listing or search query."),
    comments_per_post: int = typer.Option(50, min=1, help="Maximum comments to keep per post."),
) -> None:
    config = RedditResearchConfig()
    output_path = run_collection(config, limit=limit, comments_per_post=comments_per_post)
    console.print(f"Saved raw Reddit threads to {output_path}")


@app.command()
def analyze(
    input: Path | None = typer.Option(None, exists=True, dir_okay=False, help="Collected JSON file."),
    anonymize_usernames: bool = typer.Option(
        False,
        help="Hide usernames in the Markdown quotebook.",
    ),
) -> None:
    config = RedditResearchConfig()
    outputs = run_analysis(config, input_path=input, anonymize_usernames=anonymize_usernames)
    for label, path in outputs.items():
        console.print(f"{label}: {path}")


@app.command()
def run(
    limit: int = typer.Option(25, min=1, help="Posts per listing or search query."),
    comments_per_post: int = typer.Option(50, min=1, help="Maximum comments to keep per post."),
    anonymize_usernames: bool = typer.Option(
        False,
        help="Hide usernames in the Markdown quotebook.",
    ),
) -> None:
    config = RedditResearchConfig()
    raw_path = run_collection(config, limit=limit, comments_per_post=comments_per_post)
    console.print(f"Saved raw Reddit threads to {raw_path}")
    outputs = run_analysis(config, input_path=raw_path, anonymize_usernames=anonymize_usernames)
    for label, path in outputs.items():
        console.print(f"{label}: {path}")


if __name__ == "__main__":
    app()
