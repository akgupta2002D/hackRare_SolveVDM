from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .config import RedditResearchConfig
from .symptom_graphs import run_symptom_phrase_graph

app = typer.Typer(add_completion=False, help="Reddit research pipeline for eye floaters.")
console = Console()


@app.command()
def collect(
    limit: int = typer.Option(25, min=1, help="Posts per listing or search query."),
    comments_per_post: int = typer.Option(50, min=1, help="Maximum comments to keep per post."),
) -> None:
    from .pipeline import run_collection

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
    from .pipeline import run_analysis

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
    from .pipeline import run_analysis, run_collection

    config = RedditResearchConfig()
    raw_path = run_collection(config, limit=limit, comments_per_post=comments_per_post)
    console.print(f"Saved raw Reddit threads to {raw_path}")
    outputs = run_analysis(config, input_path=raw_path, anonymize_usernames=anonymize_usernames)
    for label, path in outputs.items():
        console.print(f"{label}: {path}")


@app.command("symptom-graph")
def symptom_graph(
    input: Path | None = typer.Option(None, exists=True, dir_okay=False, help="Collected JSON file."),
    top_n: int = typer.Option(
        12,
        min=3,
        max=40,
        help="How many top phrases to keep per category for chart/export.",
    ),
    include_comments: bool = typer.Option(
        True,
        help="Include comments in phrase counts (usually gives better signal).",
    ),
) -> None:
    config = RedditResearchConfig()
    outputs = run_symptom_phrase_graph(
        config,
        input_path=input,
        top_n=top_n,
        include_comments=include_comments,
    )
    console.print(f"csv: {outputs['csv']}")
    console.print(f"json: {outputs['json']}")
    if outputs["png"] is None:
        console.print("png: not generated (matplotlib not installed)")
    else:
        console.print(f"png: {outputs['png']}")


if __name__ == "__main__":
    app()
