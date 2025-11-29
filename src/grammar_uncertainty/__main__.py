"""
CLI entry point for Grammar Uncertainty Analyzer.
"""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="grammar-uncertainty",
    help="Analyze uncertainty in Probabilistic Context-Free Grammars derived from program source code.",
    add_completion=False,
)
console = Console()


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
):
    """Start the REST API server."""
    import uvicorn

    console.print(f"[green]Starting server at http://{host}:{port}[/green]")
    console.print("[dim]API docs available at /docs[/dim]")

    uvicorn.run(
        "grammar_uncertainty.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def analyze(
    folder_path: Path = typer.Argument(..., help="Path to folder containing program files"),
    grammar: str = typer.Option("smtlib", "--grammar", "-g", help="Grammar to use"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output JSON file"),
    no_uncertainty: bool = typer.Option(
        False, "--no-uncertainty", help="Skip uncertainty computation"
    ),
):
    """Analyze programs in a folder and compute PCFG with uncertainty metrics."""
    from grammar_uncertainty import GrammarAnalyzer

    console.print(f"[blue]Analyzing programs in {folder_path}...[/blue]")

    try:
        analyzer = GrammarAnalyzer(grammar=grammar)
        result = analyzer.analyze(
            folder_path=str(folder_path),
            compute_uncertainty=not no_uncertainty,
        )

        if result.success:
            # Print summary
            table = Table(title="Analysis Results")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Grammar", result.grammar)
            table.add_row("Programs Parsed", str(result.programs_parsed))
            table.add_row("Programs Failed", str(result.programs_failed))
            table.add_row("Total Rules", str(result.total_rules))
            table.add_row("Unique Rules", str(result.unique_rules))
            table.add_row("Analysis Time", f"{result.analysis_time_ms:.2f} ms")

            if result.uncertainty:
                table.add_row("Grammar Entropy", f"{result.uncertainty.grammar_entropy:.4f}")
                table.add_row("Perplexity", f"{result.uncertainty.perplexity:.4f}")
                table.add_row("NSUI", f"{result.uncertainty.nsui:.4f}")

            console.print(table)

            # Save output
            if output:
                result.save(str(output))
                console.print(f"[green]Results saved to {output}[/green]")
            else:
                # Default output file
                default_output = folder_path.name + "_analysis.json"
                result.save(default_output)
                console.print(f"[green]Results saved to {default_output}[/green]")

        else:
            console.print("[red]Analysis failed![/red]")
            for error in result.errors:
                console.print(f"  [red]- {error}[/red]")
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def setup(
    grammar: str = typer.Argument("smtlib", help="Grammar to set up"),
    force: bool = typer.Option(False, "--force", "-f", help="Force regeneration"),
):
    """Set up a grammar (download and generate ANTLR parser)."""
    from grammar_uncertainty.grammars import get_grammar_handler

    console.print(f"[blue]Setting up grammar: {grammar}[/blue]")

    try:
        handler = get_grammar_handler(grammar)

        if handler.is_setup_complete() and not force:
            console.print(f"[green]Grammar '{grammar}' is already set up.[/green]")
            console.print("[dim]Use --force to regenerate.[/dim]")
            return

        success = handler.setup(force=force)

        if success:
            console.print(f"[green]Grammar '{grammar}' set up successfully![/green]")
        else:
            console.print(f"[red]Failed to set up grammar '{grammar}'[/red]")
            raise typer.Exit(code=1)

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def grammars():
    """List available grammars."""
    from grammar_uncertainty.grammars import list_grammars

    table = Table(title="Available Grammars")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Extensions", style="yellow")
    table.add_column("Setup", style="green")

    for g in list_grammars():
        status = "[green]Yes[/green]" if g.is_setup else "[red]No[/red]"
        table.add_row(
            g.name,
            g.description,
            ", ".join(g.file_extensions),
            status,
        )

    console.print(table)


@app.command()
def version():
    """Show version information."""
    from grammar_uncertainty import __version__

    console.print(f"grammar-uncertainty version {__version__}")


if __name__ == "__main__":
    app()
